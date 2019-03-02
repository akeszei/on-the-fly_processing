#!/usr/bin/env bash

## A.Keszei: Updated 2019-03-02

############ Simplify text output modifiers (e.g. echo "${red}color text here,${default} default text color here");
default=$(tput sgr0)
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
magenta=$(tput setaf 5)
cyan=$(tput setaf 6)
white=$(tput setaf 7)

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C
trap "echo; echo '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM
## Automatically terminate script if any variables are undefined
set -eu

############ Introductory remarks
echo
echo "${cyan}================================================================================================================="
echo " Mark files listed in a given file with a defined suffix."
echo " The files and list should be in the same current working directory, and the list entries be of the format:"
echo "     ${red} 0002"
echo "      1074"
echo "      ####"
echo "      ... ${cyan}"
echo " Files should be of the format: ${red}Name_####.ext${cyan} (where '${red}Name${cyan}' can be of the form: ${red}Prefix_suffix1_suffix2_...${cyan})"
echo "=================================================================================================================${default}"
echo

############ User inputs the full name of the file with the listed frames (e.g. 'list.txt')
read -ep "${magenta}File with listed frames to be marked (e.g. bad_mics.txt): ${default}" list
# Input .txt file must have linux-style line endings (LF, not Windows-style CRLF). Check this is true else quit with a warning.
if [[ $(head -1 $list) == *$'\r' ]]; then
    echo
    echo "${red}!!! ERROR: ${default}File with listed frames (${magenta}$list${default}) should be in LF format (not CRLF)."; exit
fi

echo
echo "First few entries of ${magenta}$list${default} are:"
echo "====================================${cyan}"
head -3 $list # print first three lines in the user-defined text file
echo "${default}..."
echo "===================================="
echo

############ Input details of the files to be searched and changed
read -ep "${magenta}Give an example file from the batch to be modified (e.g. ${cyan}Name_0001.ext${default}${magenta}): ${default}" filename
read -ep "${magenta}Suffix to mark listed files (e.g. for ${cyan}Name_###.ext_badframe${magenta}, use:${cyan}_badframe${default}): " -i "_badframe" mark

#### From given file name, extract the prefix, and suffix (extension)
prefix="${filename%_*}_"
suffix=".${filename##*.}"

echo
echo "Files to remove are of the format:"
echo "====================================${cyan}"
echo $prefix$(awk 'NR==1 {print; exit}' $list)$suffix # add user defined extension to each item and allow user to review
echo $prefix$(awk 'NR==2 {print; exit}' $list)$suffix
echo $prefix$(awk 'NR==3 {print; exit}' $list)$suffix
echo "${default}..."
echo "===================================="

############ Logical tests to make sure user has input variables
if [ -z "$list" ]; then
      echo "Input file not specified!" ; exit
fi
if [ -z "$filename" ]; then
      echo "Input micrographs not specified!" ; exit
fi
if [ -z "$mark" ]; then
      echo "Marker string not specified!" ; exit
fi

############ Allows the user to review their actions
file="$list"
firstline=$(awk 'NR==1 {print; exit}' $list)
total_entries=$(cat $list | wc -l)
total_matching_files=$(ls -l "$prefix"*"$suffix" | wc -l)
echo "Files of the format: " "${magenta}$prefix""$firstline""$suffix${default}" " will be changed to: " "${magenta}$prefix""$firstline""$suffix""$mark${default}"
echo "  ${magenta}$total_matching_files${default} files found, with ${magenta}$total_entries${default} entries listed for modification."
read -p ">> Proceed? ${magenta}" userinput
echo "${default}"
if [ "$userinput" != "y" ] && [ "$userinput" != "yes" ] && [ "$userinput" != "Y" ] && [ "$userinput" != "Yes" ]; then
  echo "Terminating script." ; exit
fi

############ Loop through target file, assigning each line to the variable $line every iteration
while IFS= read -r line; do

    temp_var1="$prefix""$line""$suffix"    #builds the file name to be changed, with each line from the file replacing the number
    temp_var2="$prefix""$line""$suffix""$mark" #suffix appended

    # if file exists, run the 'mv' command
    if [ -f $temp_var1 ]; then
        mv -v "$temp_var1" "$temp_var2"
    else
        echo " ${red}!!! ERROR:${default} File ${cyan}$temp_var1${default} not found in current working directory, skipping ..."
    fi
done <"$file"

echo
files_w_mark=$(ls *$mark | wc -l)
echo "Job complete: ${magenta}$files_w_mark${default} files marked."
echo "If desired, remove marked files with: "
echo "    ${red}rm *$mark${default}"
echo
