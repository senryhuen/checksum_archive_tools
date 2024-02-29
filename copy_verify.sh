#! /bin/zsh

## WARNING: reserved filenames: .src_target_checksum_diffs.txt, .copy_verify_src_checksum.txt, .copy_verify_target_checksum.txt

# exit codes:
# 1: problem with $SOURCE (1st arg)
# 2: problem with $TARGET (2nd arg)
# 3: output file exists and already contains checksums for all existing files


# WARNING: will delete .DS_Store files and "._" files
# ARGS: source_path
function checksum_dir {
    SOURCE_DIR=$1
    CHECKSUM_FILENAME=$2
    SOURCE_CHECKSUM_TXT="$SOURCE_DIR/$CHECKSUM_FILENAME"

    check_dir_exists $SOURCE_DIR
    if [[ $? != 2 ]]
    then
        echo "ERROR: Directory '$SOURCE' doesn't exist or is empty"
        return 1
    fi

    cd $SOURCE_DIR

    find . -name ".DS_Store" -type f -delete
    dot_clean -m ./  # MacOS specific

    FILES=$(find . -type f ! -name $CHECKSUM_FILENAME | sort)

    check_file_exists $SOURCE_CHECKSUM_TXT
    if [[ $? == 0 ]]
    then
        NEW_FILES=$(comm -23 <(echo $FILES) <(awk -F'^.{32} ' '{print $2}' $CHECKSUM_FILENAME | sort))

        if [[ -z $NEW_FILES ]]
        then
            echo "WARNING: skipping since '$CHECKSUM_FILENAME' already exists and there are no new files"
            return 3
        else
            echo "WARNING: '$CHECKSUM_FILENAME' already exists, new checksums will be appended"
            FILES=$NEW_FILES
        fi
    fi

    echo "$(date +'%Y.%m.%d %H:%M:%S') - started checksumming $SOURCE_DIR"

    FILES_ARR=("${(@f)$(echo $FILES)}")
    for file_path in $FILES_ARR
    do
        md5 -r "$file_path" >> $CHECKSUM_FILENAME
    done

    # find . -type f ! -name $CHECKSUM_FILENAME -exec md5 -r '{}' \; > $CHECKSUM_FILENAME

    echo "$(date +'%Y.%m.%d %H:%M:%S') - finished checksumming $SOURCE_DIR"
 
    cd $OLDPWD

    return 0
}

# ARGS: source_path
function checksum_source {
    checksum_dir $1 ".copy_verify_src_checksum.txt"
    return $?
}

# ARGS: target_path
function checksum_target {
    checksum_dir $1 ".copy_verify_target_checksum.txt"
    return $?
}

# ARGS: source_path, target_path
function copy_verify {
    SOURCE=$1
    TARGET=$2

    # source needs to exist and not be empty to be copied
    check_dir_exists $SOURCE
    if [[ $? != 2 ]]
    then
        echo "ERROR: Directory '$SOURCE' doesn't exist or is empty"
        exit 1
    fi

    # target directory needs to exist to be written in
    check_dir_exists $TARGET
    if [[ $? == 0 ]]
    then
        echo "ERROR: Directory '$TARGET' doesn't exist"
        exit 2
    fi

    # directory to be copied cannot already exist in target directory (collision)
    FINAL_DIR="$TARGET/$(basename $SOURCE)"
    check_dir_exists $FINAL_DIR
    if [[ $? != 0 ]]
    then
        echo "ERROR: Copy already exists at '$TARGET' Directory"
        exit 2
    fi

    # check that file to write diffs to (between $SOURCE and $TARGET checksums) will not exist in $TARGET
    DIFF_TXT="$SOURCE/.src_target_checksum_diffs.txt"
    check_file_exists $DIFF_TXT
    if [[ $? == 0 ]]
    then
        echo "ERROR: '$DIFF_TXT' file already exists, which will cause conflict with generated files"
        exit 3
    fi

    checksum_source $SOURCE  # will skip if checksum file already exists (assumes up to date)

    ## rsync -hvac --info=progress2 $SOURCE $TARGET &&  # verbose per file as it is being transferred
    rsync -hac --info=progress2 $SOURCE $TARGET && 

    checksum_target $FINAL_DIR
    
    CHECKSUM_COMP="$FINAL_DIR/.copy_verify_src_checksum.txt"
    TARGET_CHECKSUM="$FINAL_DIR/.copy_verify_target_checksum.txt"
    DIFF_TXT="$FINAL_DIR/.src_target_checksum_diffs.txt"

    comm -23 <(sort $CHECKSUM_COMP) <(sort $TARGET_CHECKSUM) > $DIFF_TXT
}

function verify_source {
    SOURCE=$1

    CHECKSUM_COMP="$SOURCE/.copy_verify_src_checksum.txt"
    TARGET_CHECKSUM="$SOURCE/.copy_verify_target_checksum.txt"
    DIFF_TXT="$SOURCE/.src_target_checksum_diffs.txt"

    # check that file to write diffs to (between existing and new checksums) does not already exist
    check_file_exists $DIFF_TXT
    if [[ $? == 0 ]]
    then
        echo "ERROR: '$DIFF_TXT' file already exists, which will cause conflict with generated files"
        exit 3
    fi
    
    # check file of source checksum exists
    check_file_exists $CHECKSUM_COMP
    if [[ $? == 1 ]]
    then
        echo "ERROR: '$CHECKSUM_COMP' file not found"
        exit 3
    fi

    checksum_target $SOURCE

    comm -23 <(sort $CHECKSUM_COMP) <(sort $TARGET_CHECKSUM) > $DIFF_TXT
}

# ARGS: directory_path
# RETURNS: 0-does not exist, 1-exists and is empty, 2-exists and is not empty
function check_dir_exists {
    DIR=$1
    
    if [[ -d "$DIR" ]]
    then
        if [[ "$(ls -A $DIR)" ]]
        then
            # $DIR exists and is not empty
            return 2
        else
            # $DIR exists and is empty
            return 1
        fi
    else
        # $DIR does not exist
        return 0
    fi
}

# ARGS: file_path
# RETURNS: 0-file exists, 1-file does not exist
function check_file_exists {
    FILE=$1

    if [[ -f "$FILE" ]]
    then
        # file exists
        return 0
    else
        # file does not exist
        return 1
    fi
}
