#!/usr/bin/env python
DESC_STR = \
"""
Divide a directory into lists of a max combined file size. See README.org
for full details.
"""

import os
import argparse
import subprocess
import collections

Node = collections.namedtuple( "Node", [ "path", "size" ] )

def run_cmd( command ):
    """
    Wrapper for subprocess.check_output that returns a string.
    """
    return subprocess.check_output( command ).decode( "utf-8" )

def get_size_bytes( path ):
    """
    Gets the size of a file or directory (and it's contents,
    recursively) in bytes. Calls the 'du' utility.
    """
    cmd = [ 'du',  '-s',  '-B1',  '--apparent-size', path ]
    return int( run_cmd( cmd ).split( "\t" )[ 0 ] )

def immediate_children( path ):
    """
    Return a list of strings. Each string is an immediate child
    of the given path.
    """
    assert( os.path.isdir( path ) )
    CMD = [ "find", path, "-mindepth", "1", "-maxdepth", "1" ]
    return [ x for x in run_cmd( CMD ).split( "\n" ) if len( x ) > 0 ]

def split_all( path ):
    """
    Given a path, split into all parts.
    """
    ret = []
    while True:
        head, tail = os.path.split( path )
        if len( tail ) > 0:
            ret.append( tail )
        if head == path:
            ret.append( head )
            break
        path = head
    return ret[::-1]

def lsize( lst ):
    """
    Combined size of all Nodes in a list
    """
    return sum( [ x[1] for x in lst ] )

def sort_siblings( siblings ):
    """
    File groups large to small, then mixed groups large to small.
    """
    def files_only_pred( lst ):
        return all( [ not os.path.isdir( x[0] ) for x in lst ] )
    file_only_siblings = [ s for s in siblings if files_only_pred( s ) ]
    mixed_siblings     = [ s for s in siblings if not files_only_pred( s ) ]
    return sum( [ sorted( lst, key=lambda x:-lsize( x ) ) for lst in [ file_only_siblings, mixed_siblings ] ], [] )

def toplevel_subdir( path, target_dir ):
    """
    Given /a/b/c and /a/b/c/d/e/f, return d
    """
    parts = split_all( path )
    rparts = split_all( target_dir )
    assert( rparts == parts[ :len( rparts ) ] )
    return parts[ len( rparts ) ]

def valid_merge( group1, group2, target_dir, max_list_size, split_toplevel=True ):
    """
    Determine whether these groups can be merged.
    """
    if len( group1 ) <= 0 or len( group2 ) <= 0:
        return True
    if ( lsize( group1 ) + lsize( group2 ) ) <= max_list_size:
        return ( not split_toplevel ) or toplevel_subdir( group1[0].path, target_dir ) == toplevel_subdir( group2[0].path, target_dir )
    return False

def group_siblings( siblings, target_dir, max_list_size, split_toplevel ):
    """
    Merge lists of nodes such that each list remains less than
    max_list_size, but in as few lists as possible.
    """
    lists = []
    siblings = sort_siblings( siblings )
    assert( all( [ lsize( group ) <= max_list_size for group in siblings ] ) )
    while len( siblings ) > 0:
        siblings_new = []
        merged_group = []
        for group in siblings:
            if valid_merge( merged_group, group, target_dir, max_list_size, split_toplevel=split_toplevel ):
                merged_group += group
            else:
                siblings_new.append( group )
        lists.append( merged_group )
        siblings = siblings_new
    return lists

def get_node_lists( node, target_dir, max_list_size ):
    """
    Get proper sublists for node.
    """
    if node.size <= max_list_size:
        return [ [ node ] ]
    else:
        if not os.path.isdir( node.path ):
            print( "Error: Encountered file larger than max list size!\n{}".format( node.path ) )
            exit( -1 )
        children =  [ Node( c, get_size_bytes( c ) ) for c in immediate_children( node.path ) ]
        ret = []
        for c in children:
            ret.extend( get_node_lists( c, target_dir, max_list_size ) )
        return group_siblings( ret, target_dir, max_list_size, True )

def get_file_lists( target_dir, max_list_bytes ):
    """
    entry point
    """
    node_lists = get_node_lists( Node( target_dir, get_size_bytes( target_dir ) ), target_dir, max_list_bytes )
    node_lists = group_siblings( node_lists, target_dir, max_list_bytes, False )
    node_lists = [ [ x[0] for x in y ] for y in node_lists ]
    return node_lists

def bytes_from_str( size_str ):
    """
    Given a string description of directory size, return float bytes.
    Supports B, K, M, G, T suffixes. B can be ommitted.
    """
    unit_conversions = { char: 1024**power for ( power, char ) in enumerate( [ "B", "K", "M", "G", "T" ] ) }
    try:
        coeff = unit_conversions[ size_str.upper()[-1] ]
        size_str = size_str[:-1]
    except KeyError:
        coeff = 1
    try:
        size = float( size_str )
    except ValueError:
        print( "Invalid size string: {}".format( size_str ) )
        exit( -1 )
    return coeff * size

def insert_rsync_marker( path, target_dir ):
    """
    Insert /./ in path where target_dir ends. This causes rsync to preserve
    the following directories when copying.
    """
    rel_cutoff = len( split_all( target_dir ) )
    parts = split_all( path )
    parts.insert( rel_cutoff, "." )
    return os.path.join( *parts )

def write_manifests( file_lists, target_dir, output_dir ):
    """
    Write a list of manifests to files in output_dir. They are relative to the target directory,
    and compatible with rsync.
    """
    for i, lst in enumerate( file_lists ):
        with open( os.path.join( output_dir, "manifest-{}.txt".format( i ) ), "w" ) as fout:
            for r in lst:
                fout.write( insert_rsync_marker( r, target_dir ) + "\n" )

def write_map( file_lists, target_dir, output_dir ):
    """
    Write a map indicating where the contents of top-level subdirectories
    are distributed.
    """
    tld_to_volumes = {}
    for i, group in enumerate( file_lists ):
        for node in group:
            tld = toplevel_subdir( node, target_dir )
            tld_to_volumes.setdefault( tld, set() ).add( i )
    with open( os.path.join( output_dir, "map.txt" ), "w" ) as fout:
        for tld, volumes in tld_to_volumes.items():
            fout.write( "{:24s}: {}\n".format( tld, " ".join( [ str( x ) for x in volumes ] ) ) )

if __name__ == "__main__":
    parser = argparse.ArgumentParser( description=DESC_STR )
    parser.add_argument( 'directory', type=str, help="Directory to split." )
    parser.add_argument( 'size',      type=str, help="Max list size, like 24k or 52G" )
    parser.add_argument( 'dest',      type=str, help="Directory in which manifests will be written." )
    args = parser.parse_args()

    fl = get_file_lists( args.directory, bytes_from_str( args.size ) )
    write_manifests( fl, args.directory, args.dest )
    write_map( fl, args.directory, args.dest )
