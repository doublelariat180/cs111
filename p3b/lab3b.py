#!/usr/bin/python
from __future__ import print_function
import sys
import csv

'''
    TA SLIDES/PSUEDOCODE
    INVALID BLOCK 101 IN INODE 13 AT OFFSET 0
	INVALID INDIRECT BLOCK 101 IN INODE 13 AT OFFSET 12
	INVALID DOUBLE INDIRECT BLOCK 101 IN INODE 13 AT OFFSET 268
	INVALID TRIPLE INDIRECT BLOCK 101 IN INODE 13 AT OFFSET 65804
	RESERVED INDIRECT BLOCK 3 IN INODE 13 AT OFFSET 12
	RESERVED DOUBLE INDIRECT BLOCK 3 IN INODE 13 AT OFFSET 268
	RESERVED TRIPLE INDIRECT BLOCK 3 IN INODE 13 AT OFFSET 65804
	RESERVED BLOCK 3 IN INODE 13 AT OFFSET 0
    UNREFERENCED BLOCK 37
    ALLOCATED BLOCK 8 ON FREELIST
    DUPLICATE BLOCK 8 IN INODE 13 AT OFFSET 0
	DUPLICATE INDIRECT BLOCK 8 IN INODE 13 AT OFFSET 12
	DUPLICATE DOUBLE INDIRECT BLOCK 8 IN INODE 13 AT OFFSET 268
	DUPLICATE TRIPLE INDIRECT BLOCK 8 IN INODE 13 AT OFFSET 6580
    ALLOCATED INODE 2 ON FREELIST
	UNALLOCATED INODE 17 NOT ON FREELIST
    INODE 2 HAS 4 LINKS BUT LINKCOUNT IS 5
    INODE 17 HAS 0 LINKS BUT LINKCOUNT IS 1
    DIRECTORY INODE 2 NAME 'nullEntry' UNALLOCATED INODE 17
	DIRECTORY INODE 2 NAME 'bogusEntry' INVALID INODE 26
    DIRECTORY INODE 2 NAME '..' LINK TO INODE 11 SHOULD BE 2
	DIRECTORY INODE 11 NAME '.' LINK TO INODE 2 SHOULD BE 11

    possible errors block errors
        invalid
            block number < 0 or > block count
        reserved
            block number is used by boot block, sb, bgt, inode bitmap, block bitmap, or inode table
        unreferenced
            not referenced by any file but marked as allocated by bitmap
        allocated
            allocated to file but marked as free on bitmap
        duplicate
            used by more than two files

    inode errors
        if imode == 0 inode is free, else used
        allocated
            imode != 0 but marked as free on inode bitmap
        unallocated
            imode ==0 but marked as used on inode bitmap

    directory errors
        going to use inode number in DIRENTRY and link count in INODE
        incorrect links count
            number of dir_entry pointing to the inode is not the same as ilinkscount
        unallocated
            inode referenced in dir_entry is marked as free in inode bitmap
        invalid
            inode referenced in direntry is <0 or >mac inode number from SUPERBLOCK
        . is not pointing to current directory and .. is not pointing to the parent DIRECTORY

data block number psuedo code
max_block = sb.s_blocks_count
orig_block_bitmap = block_bit_map
create empty my_block_bitmap
reserved_bit_map = calc_reserved_bit_map()//block numbers used by boot block, sb, etc

for every inode
    if inode is not used
        continue

    for every data block in inode
        if blocknum < 0 or block num > max_block
            report invalid
        if block number in reserved bitmap
            report reserved
        if block number is free in original block bitmap
            report allocated
        if block number is marked as used in my block bitmap
            report duplicated

        mark block number as used in my block bitmap

for block in my block bitmap
    if(block number marked as used in original block bitmap && block number is free in my block bitmap)
        report unreferenced

inode errors psuedo code
original inode bitmap = inode bitmap
for every inode
    if inode imode != 0 and inode marked as free in orig inode bitmap
        report allocated
    else if inode imode == 0 and inode marked as used in original inode bitmap
        report unallocated

max inode = super block iniode count
create inode reference array
create inode parent array
for every inode
    if inode is not directory
        continue
    par_inode = inode.i_ino
    for every directory entry in inode
        child_ino = dir_entry.inode
        child_name = dir_entry.name
        if child_ino < 0 or child_ino > max_inode
            report invalid
        if child inode is free in inode_bitmap
            report unallocated
        if child name is '.' and child_ino != par_ino
            report current mismatch
        if child_name is not '.' and child name is not '..'
            inode_ref_array[child_ino]++
        inode_par_array[child_ino] = par_ino

for every inode
    par_ino = inode number of current dir
    if inode _ref_array[par_inode] != inode.i_links_count
        report inocrrect_link_count
    if(inode not directory)
        continue
    for every directory entry in inode
        child_ino = dir_entry.inode #inode number of each child entry in the current dir
        child_name = dir_entry.name
        if child_name is '..' && child_ino != inode_par_array[par_ino]
            report parrent_mismatch
'''

corrupt = 0

if len(sys.argv) != 2:
    print('Bad Arguments', file=sys.stderr)
    exit(1)

if sys.argv[1][-4:] != ".csv":
    print('Bogus Arguments', file=sys.stderr)
    exit(1)

csv_file = open(sys.argv[1], 'r')#gets file object
csv_reader = csv.reader(csv_file)

max_block = 0
num_reserved = 0
max_inode = 0
block_size = 0
first_inode = 0
bfree_list = []
ifree_list = []
inode_list = []
dirent_list = {}
indirect_list = []
for line in csv_reader:
    #add each type to appropriate list
    n = line[0]
    if n == 'SUPERBLOCK':
        max_block = int(line[1])
        num_reserved = 4 + int(line[6])/(int(line[3])/int(line[4])) #5+number of blocksoccupied by inode table ie boot + super + groupdesc
        max_inode = int(line[2])
        block_size = int(line[3])
        first_inode = int(line[7])
    elif n == 'BFREE':
        bfree_list.append(int(line[1]))
    elif n == 'IFREE':
        ifree_list.append(int(line[1]))
    elif n == 'INODE':
        inode_list.append(line)
    elif n == 'DIRENT':
        if int(line[1]) in dirent_list:
            dirent_list[int(line[1])].append(line)
        else:
            dirent_list[int(line[1])] = list()
    elif n == 'INDIRECT':
        indirect_list.append(line)


#check blocks of inodes
my_block_bitmap = []
dup_list = []
for inode in inode_list:
    for i in range(12, 27):
        block = int(inode[i])
        if i == 24:
            ind_level = 'INDIRECT '
            offset = 12
        elif i == 25:
            ind_level = 'DOUBLE INDIRECT '
            offset = 12 + block_size/4
        elif i == 26:
            ind_level = 'TRIPLE INDIRECT '
            offset = 12 + (block_size/4) + (block_size/4)*(block_size/4)
        else:
            ind_level = ''
            offset = 0

        if block == 0: #unused block
            continue
        #print('current block is ' + str(block))
        if block < 0 or block > max_block:
            print('INVALID ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(inode[1]) + ' AT OFFSET ' + str(offset))
            corrupt = 2
        if block <= num_reserved:
            print('RESERVED ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(inode[1]) + ' AT OFFSET ' + str(offset))
            corrupt = 2
        if block in bfree_list:
            print('ALLOCATED BLOCK ' + str(block) + ' ON FREELIST')
            corrupt = 2
        if block in my_block_bitmap:
            #print('DUPLICATE ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(inode[1]) + ' AT OFFSET ' + str(offset))
            dup_list.append(int(block))
            corrupt = 2
        my_block_bitmap.append(int(block))


#check blocks indirectly referenced
for indirect in indirect_list:
    block = int(indirect[5]) #block#
    if int(indirect[2]) == 1:
        ind_level = 'INDIRECT '
        offset = 12
    elif int(indirect[2]) == 2:
        ind_level = 'DOUBLE INDIRECT '
        offset = 12 + int(inode[3])/4
    elif int(indirect[2]) == 3:
        ind_level = 'TRIPLE INDIRECT '
        offset = 12 + (int(inode[3])/4) + (int(inode[3])/4)*(int(inode[3])/4)
    else:
        ind_level = ''
        offset = 0

    if block == 0: #unused block
        continue
    if int(block) < 0 or int(block) > max_block:
        print('INVALID ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(indirect[1]) + ' AT OFFSET ' + str(offset))
        corrupt = 2
    if int(block) <= num_reserved:
        print('RESERVED ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(indirect[1]) + ' AT OFFSET ' + str(offset))
        corrupt = 2
    if int(block) in bfree_list:
        print('ALLOCATED BLOCK ' + str(block) + ' ON FREELIST')
        corrupt = 2
    if int(block) in my_block_bitmap:
        #print('DUPLICATE ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(indirect[1]) + ' AT OFFSET ' + str(offset))
        dup_list.append(int(block))
        corrupt = 2
    my_block_bitmap.append(int(block))


#find dups
for inode in inode_list:
    for i in range(12, 27):
        block = int(inode[i])
        if i == 24:
            ind_level = 'INDIRECT '
            offset = 12
        elif i == 25:
            ind_level = 'DOUBLE INDIRECT '
            offset = 12 + block_size/4
        elif i == 26:
            ind_level = 'TRIPLE INDIRECT '
            offset = 12 + (block_size/4) + (block_size/4)*(block_size/4)
        else:
            ind_level = ''
            offset = 0
        if block == 0: #unused block
            continue
        if block in dup_list:
            print('DUPLICATE ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(inode[1]) + ' AT OFFSET ' + str(offset))
for indirect in indirect_list:
    block = int(indirect[5]) #block#
    if int(indirect[2]) == 1:
        ind_level = 'INDIRECT '
        offset = 12
    elif int(indirect[2]) == 2:
        ind_level = 'DOUBLE INDIRECT '
        offset = 12 + int(inode[3])/4
    elif int(indirect[2]) == 3:
        ind_level = 'TRIPLE INDIRECT '
        offset = 12 + (int(inode[3])/4) + (int(inode[3])/4)*(int(inode[3])/4)
    else:
        ind_level = ''
        offset = 0
    if block == 0: #unused block
        continue
    if block in dup_list:
        print('DUPLICATE ' + ind_level + 'BLOCK ' + str(block) + ' IN INODE ' + str(indirect[1]) + ' AT OFFSET ' + str(offset))

#check blocks that arent listed as free or occupied, ie block is used but no inode points to it directly or indirectly
for i in range(num_reserved+1, max_block):
    if i not in bfree_list and i not in my_block_bitmap:
        print('UNREFERENCED BLOCK ' + str(i))
        corrupt = 2



#inodes not listed on free list or inode summary
ir_list = []
for i in range(first_inode, max_inode+1):
    ir_list.append(i)
for i in ifree_list:
    if i in ir_list:
        ir_list.remove(i)
for inode in inode_list:
    if int(inode[1]) in ir_list:
        ir_list.remove(int(inode[1]))
for i in ir_list:
    print('UNALLOCATED INODE ' + str(i) + ' NOT ON FREELIST')
    corrupt = 2


#inode that is occupied but is marked free
reported_list = []
for inode in inode_list:
    if int(inode[3]) != 0 and int(inode[1]) in ifree_list:
        print('ALLOCATED INODE ' + str(inode[1]) + " ON FREELIST")
        reported_list.append(int(inode[1]))
        corrupt = 2


#check inodes
iref_array = {}
ipar_array = {}
for inode in inode_list:
    if inode[2] != 'd':
        continue
    par_inode = int(inode[1])
    if par_inode in iref_array:
        iref_array[par_inode] += 1
    else:
        iref_array[par_inode] = 1
    for de in dirent_list[int(inode[1])]:
        child_ino = int(de[3]) #sus
        child_name = de[6]
        if child_ino < 0 or child_ino > max_inode:
            print('DIRECTORY INODE ' + str(par_inode) + ' NAME ' + str(child_name) + ' INVALID INODE ' + str(child_ino))
            corrupt = 2
        if child_ino in ifree_list and child_ino not in reported_list:#check here
            print('DIRECTORY INODE ' + str(par_inode) + ' NAME ' + str(child_name) + ' UNALLOCATED INODE ' + str(child_ino))
            corrupt = 2
        if child_name == '.' and child_ino != par_inode:
            print('DIRECTORY INODE' + str(par_inode) + 'NAME \'.\' LINK TO INODE ' + str(child_ino) + ' SHOULD BE ' + str(par_inode))
            corrupt = 2
        if par_inode == 2 and child_name == "'..'" and child_ino != par_inode:#2 is root dir so it is its own parent#why do i need "" here but not in other areas
            print('DIRECTORY INODE ' + str(par_inode) + ' NAME \'..\' LINK TO INODE ' + str(child_ino) + ' SHOULD BE ' + str(par_inode))
            corrupt = 2
        if child_name != '.' and child_name != '..':
            if child_ino in iref_array:
                iref_array[child_ino] += 1
            else:
                iref_array[child_ino] = 1
        ipar_array[child_ino] = par_inode

#check inodes that arent direcotries and dirents
for inode in inode_list:
    if inode[2] != 'd':
        if int(inode[1]) not in iref_array:
            print('INODE ' + str(inode[1]) + ' HAS ' + str(0) + ' LINKS BUT LINKCOUNT IS ' + str(inode[6]))
            corrupt = 2
        elif iref_array[int(inode[1])] != int(inode[6]):
            print('INODE ' + str(inode[1]) + ' HAS ' + str(iref_array[par_inode]) + ' LINKS BUT LINKCOUNT IS ' + str(inode[6]))
            corrupt = 2
        continue
    par_inode = int(inode[1])
    if iref_array[par_inode] != int(inode[6]):
        print('INODE ' + str(inode[1]) + ' HAS ' + str(iref_array[par_inode]) + ' LINKS BUT LINKCOUNT IS ' + str(inode[6]))
        corrupt = 2
    for de in dirent_list[int(inode[1])]:
        child_ino = int(de[3])
        child_name = de[6]
        if child_name == '..' and par_inode != ipar_array[child_ino]:
            print('DIRECTORY INODE' + str(par_inode) + 'NAME \'..\' LINK TO INODE ' + str(child_ino) + ' SHOULD BE ' + str(par_inode))
            corrupt = 2


exit(corrupt)
