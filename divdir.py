#!/usr/bin/env python
#
# divdir.py
#
#

DESC_STR = \
"""
Divide a directory into lists of a max combined file size. Try to
keep top-level subdirectories on as few lists as possible.

For example, if /target/a and /target/b can fit in the same list, do
it. However, if /target/a needs to be split over multiple disks, then
split it over as few as possible.

NOTE: Requires various Linux (or at least POSIX) utilities, including:
  - du
  - find
"""

import os
import argparse
import subprocess

def run_cmd( command ):
    """
    Wrapper for subprocess.check_output that returns a string.
    """
    return subprocess.check_output( command ).decode( "utf-8" )

def is_dir( node ):
    """
    Is this a directory? As opposed to a file.
    """
    return os.path.isdir( node )

def get_size_bytes( node ):
    """
    Gets the size of a file or directory (and it's contents,
    recursively) in bytes. Calls the 'du' utility.
    """
    CMD = [ 'du',  '-s',  '-B1',  '--apparent-size', node ]
    return int( run_cmd( CMD ).split( "\t" )[ 0 ] )

def flat_file_list( node ):
    """
    Return a list of strings. Each string is a descendent of the
    passed path (IE recursive). Paths are relative to the given
    path.
    """
    CMD = [ "find", node ]
    return run_cmd( CMD ).split( "\n" )

def immediate_children( node ):
    """
    Return a list of strings. Each string is an immediate child
    of the given path.
    """
    assert( is_dir( node ) )
    CMD = [ "find", node, "-mindepth", "1", "-maxdepth", "1" ]
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

def bytes_from_str( size_str ):
    """
    Given a string description of directory size, return an integer
    number of bytes.
    1T -> 1024G
    1G -> 1024M
    1M -> 1024K
    1K -> 1024
    """
    unit_conversions = {}
    basis = 1024
    for unit in [ "K", "M", "G", "T" ]:
        unit_conversions[ unit ] = basis
        basis *= 1024

    coeff = 1
    size_str = size_str.upper()
    if size_str[ -1 ] in unit_conversions.keys():
        coeff = unit_conversions[ size_str[-1] ]
        size_str = size_str[:-1]

    try:
        size = float( size_str )
    except ValueError:
        print( "Invalid size string: {}".format( size_str ) )
        exit( -1 )

    return coeff * size

def lsize( lst ):
    return sum( [ x[1] for x in lst ] )

def sort_siblings( siblings ):
    """
    Control the order in which we attempt to pack node lists.
    """
    # Files first
    # Smaller files first
    def files_only_pred( lst ):
        return all( [ not is_dir( x[0] ) for x in lst ] )
    def srt( lst ):
        return sorted( lst, key=lambda x: lsize( x ) )[::-1]
    file_only_siblings = [ s for s in siblings if files_only_pred( s ) ]
    mixed_siblings     = [ s for s in siblings if not files_only_pred( s ) ]
    return srt( file_only_siblings ) + srt( mixed_siblings )

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
    if len( group1 ) == 0 or len( group2 ) == 0:
        return True
    if ( lsize( group1 ) + lsize( group2 ) ) <= max_list_size:
        if not split_toplevel:
            return True
        path_first_g1 = split_all( group1[ 0 ][ 0 ] )
        path_first_g2 = split_all( group2[ 0 ][ 0 ] )
        target_parts  = split_all( target_dir )
        assert( target_parts == path_first_g1[ :len( target_parts ) ] )
        assert( target_parts == path_first_g2[ :len( target_parts ) ] )
        g1 = path_first_g1[ len( target_parts ): ]
        g2 = path_first_g2[ len( target_parts ): ]
        return g1[0] == g2[0]
    return False

def group_siblings( siblings, target_dir, max_list_size, split_toplevel=True, verbose=False ):
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
                if verbose:
                    print( "Can't merge {} into {}".format( merged_group, group ) )
                siblings_new.append( group )
        lists.append( merged_group )
        siblings = siblings_new
    return lists

def get_node_lists( node, target_dir, max_list_size ):
    """
    Get proper sublists for node.
    """
    if node[1] <= max_list_size:
        return [ [ node ] ]
    else:
        if not is_dir( node[0] ):
            print( "Error: Encountered file larger than max list size!\n{}".format( node[0] ) )
            exit( -1 )
        children =  [ ( c, get_size_bytes( c ) ) for c in immediate_children( node[0] ) ]
        ret = []
        for c in children:
            ret.extend( get_node_lists( c, target_dir, max_list_size ) )
        return group_siblings( ret, target_dir, max_list_size, split_toplevel=True )

def get_file_lists( target_dir, max_list_bytes ):
    """
    entry point
    """
    node_lists = get_node_lists( ( target_dir, get_size_bytes( target_dir ) ), target_dir, max_list_bytes )
    node_lists = group_siblings( node_lists, target_dir, max_list_bytes, split_toplevel=False )
    node_lists = [ [ x[0] for x in y ] for y in node_lists ]
    return node_lists

def write_manifests( file_lists, target_dir, output_dir ):
    """
    Write a list of manifests to files in output_dir. They are relative to the target directory,
    and compatible with rsync.
    """
    rel_cutoff = len( split_all( target_dir ) )
    for i, lst in enumerate( file_lists ):
        with open( os.path.join( output_dir, "manifest-{}.txt".format( i ) ), "w" ) as fout:
            for r in lst:
                parts = split_all( r )
                parts.insert( rel_cutoff, "." )
                fout.write( os.path.join( *parts ) + "\n" )

def write_map( file_lists, target_dir, output_dir ):
    """
    Write a map indicating where the contents of top-level subdirectories
    are distributed.
    """
    contents = {}
    for i, fl in enumerate( file_lists ):
        for node in fl:
            tld = toplevel_subdir( node, target_dir )
            if tld not in contents:
                contents[ tld ] = set()
            contents[ tld ].add( i )
    with open( os.path.join( output_dir, "map.txt" ), "w" ) as fout:
        for k in contents:
            fout.write( "{:24s}: ".format( k ) )
            fout.write( " ".join( [ str( x ) for x in contents[ k ] ] ) )
            fout.write( "\n" )

if __name__ == "__main__":

    # Parse CLI
    parser = argparse.ArgumentParser( description=DESC_STR )
    parser.add_argument( 'directory', type=str, help="Directory to split." )
    parser.add_argument( 'size',      type=str, help="Max list size, like 24k or 52G" )
    parser.add_argument( 'dest',      type=str, help="Directory in which manifests will be written." )
    args = parser.parse_args()

    # Get file lists & write them
    fl = get_file_lists( args.directory, bytes_from_str( args.size ) )
    write_manifests( fl, args.directory, args.dest )
    mp = write_map( fl, args.directory, args.dest )
