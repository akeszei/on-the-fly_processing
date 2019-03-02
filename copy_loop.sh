#!/usr/bin/env bash

## A.Keszei: Updated 2019-03-02

############ Simplify text output modifiers (e.g. echo "${red}color text here,${default} normal text color here");
default=$(tput sgr0)
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
cyan=$(tput setaf 4)
magenta=$(tput setaf 5)
cyan=$(tput setaf 6)
white=$(tput setaf 7)


## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo; echo '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM
## Automatically terminate script if any variables are undefined
set -eu

############ Introductory remarks
echo
echo "${cyan}==================================================================================================="
echo " Use this script to continuously copy files from a source directory to a destination directory."
echo " User defines whether to use ${red}cp${cyan} or ${red}rsync${cyan} to copy entire directory structures"
echo " into a source directory. Use ${red}rsync${cyan} only for copying via ${red}ssh protocol${cyan} as "
echo " ${red}cp${cyan} is faster when copying to a mounted drive."
echo "===================================================================================================${default}"
echo

############ Choose copy protocol & designate SOURCE and DEST paths
read -ep "${magenta}Copy protocol to use: cp, rsync: ${default}" -i "cp" copy_protocol
case $copy_protocol in
    cp )    read -ep "${magenta}Full SOURCE path (e.g. /raidy/Alex/img_dir/ ; or ./): ${default}" source_path
            read -ep "${magenta}Full DEST path (e.g. ~/F20/img_dir/ ; or ./): ${default}" dest_path
            echo

            ############ Designate the size of SOURCE and DEST as variables for later use
            source_size=$( du -hc ${source_path} | tail -1 | while read out1 out2; do echo $out1; done )
            dest_size=$( du -hc ${dest_path} | tail -1 | while read out1 out2; do echo $out1; done )
            source_filenum=$( ls -A ${source_path} | wc -l )
            dest_filenum=$( ls -A ${dest_path} | wc -l ) # note -A tells to ignore implied '.' '..' in list printout

            ############ Sanity check
            printf "Source files (${magenta}${source_filenum}${default} files, ${magenta}${source_size}${default}) will be copied into destination folder (${magenta}${dest_path}${default}, currently ${magenta}${dest_size}${default}) %s\n"
            echo "     Example command: ${red} cp -puv ${source_path}{files} $dest_path ${default}"
            read -p ">> Proceed? ${magenta}" userinput
            echo "${default}"
            if [ "$userinput" != "y" ] && [ "$userinput" != "yes" ] && [ "$userinput" != "Y" ] && [ "$userinput" != "Yes" ]; then
              echo "Terminating script." ; exit
            fi

            ############ Logical tests to make sure user has defined all necessary variables
            if [ -z "$source_path" ]; then
                  echo "${red}Source path not given!${default}" ; exit
            fi
            if [ -z "$dest_path" ]; then
                  echo "${red}Destination path not given!${default}" ; exit
            fi

            ############ Copy loop
            while sleep 2; do cp -puvr $source_path $dest_path
            printf '.' # prints a 'loading bar' style dot to let the user know the script is actively running
            done
            ;;
    rsync ) read -ep "${magenta}Full SOURCE path (e.g. dir/img_dir/; or .): ${default}" source_path
            read -ep "${magenta}Full DEST path (e.g. sshao@dug.hms.harvard.edu:\"/run/media/sshao/Seagate\ Backup\ Plus\ Drive1/data\"): ${default}" dest_path
            echo
            while sleep 5; do rsync -vahuP $source_path $dest_path; done
            ;;
    * ) echo "${red}Unrecognized copy protocol given.${default}" ; exit ;;
esac
