# Checksum-Archive-Tools

Group of packages to enable various features like efficiently generating checksums for a directory by loading saved checksums from another source, and also verifying saved checksums.  


## Main Features

### In 'md5files/checksums.py':
generate_checksums:  
* creates MD5 checksum file which will contain checksums for all files in the folder, including files in nested directories

nest_checksums:  
* creates a nested checksum file within each sub-directory, which contains checksums for just that single directory, ignoring nested directories (which would have their own nested checksum file), so that a directory can be moved whilst keeping its saved checksums intact

verify_checksums:  
* compare files to their saved checksums to verify that they have not been changed or corrupted


## Other Notable Features

### In 'utils/other.py':
get_dir_size:  
* gets filesize of a directory (all of its contents combined in GiBs

concat_filepaths:  
* concatenate filepaths with absolute paths treated equally

append_unique_lines_to_file:  
* appends/writes lines to a file if they do not already exist in the file


## Usage
Python package requirements are in 'requirements.txt'.  
For detailed usage of individual functions, refer to their docstrings.  

---

## Main Features of 'copy_verify.sh' (zsh):
copy_verify:  
* copies a directory, then verifies the transfer by comparing checksums of source and copied directory


## Usage for 'copy_verify.sh'
To use the functions defined within a shell script, you need to 'source' it within the shell/terminal:  

    source ./copy_verify.sh

After sourcing 'copy_verify.sh', you will be able to use the functions as if they were native shell commands. For example:  

    copy_verify /path/to/src /path/to/target

The command above will copy the directory 'src' to inside 'target', so the path of the copied directory (final directory) would be '/path/to/target/src'. The command will also compare checksums after copying, and any files + checksums from the source that are not in the target checksums will be written to a file in the copied directory named '.src_target_checksum_diffs.txt'. Checksums for the source directory will be calculated before the file transfer, and target checksums are calculated after.  

Source checksums are saved in '.copy_verify_src_checksum.txt' in both the source and copied directory, and the target checksums are saved in just the copied directory in '.copy_verify_target_checksum.txt'.  

Checksums for the source can be calculated separately first:  

    checksum_source /path/to/src

The 'copy_verify' command will automatically use the file generated from this command and skip checksumming the source again. This allows part of the checksumming to be done separately from the rest of the copy/verify process which may take a long time. This is also useful in situations like:  
* target directory is on a hard disk different to source; the hard disk of target directory would not need to be connected or spinning whilst it is not in use
* a source is being copied to multiple targets; the same checksum file can be used each time

### Warnings for 'copy_veryify.sh':
* The filenames: '.src_target_checksum_diffs.txt', '.copy_verify_src_checksum.txt' and '.copy_verify_target_checksum.txt' are reserved
* If files are added or removed from a directory, checksums will need to be deleted then redone
    * A manual work-around/alternative is to use 'generate_checksums' in '/md5files/checksums.py' with the old checksum file as the 'unsorted_md5_file', then rename the outputted file to '.src_target_checksum_diffs.txt'
