#!/usr/bin/env bash

## A.Keszei: Updated 2019-03-02

############ Set global variables
TIMEFORMAT='%0lR' # set output of bash built-in 'time' command to hr:min:sec
VERBOSE=false

############ Simplify text output modifiers (e.g. echo "${red}color text here,${default} normal text color here");
default=$(tput sgr0)
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
magenta=$(tput setaf 5)
cyan=$(tput setaf 6)
white=$(tput setaf 7)

############ Introductory remarks
echo
echo "${cyan}==============================================================================================="
echo " Continuously scan a directory for ${red}.TIF${cyan} micrographs and send them for processing."
echo " By default, images are binned 2x, and saved into ${red}./on-the-fly_processing/${cyan}"
echo " For speed, dose weighting is not implemented during motion correction."
echo " Quick, non-exhaustive CTF fitting is done for image quality assessment"
echo " Output data is logged in ${red}on-the-fly_data.log${cyan} and is viewable via ${red}on-the-fly_logviewer.py${cyan}"
echo "===============================================================================================${default}"
echo

############ User input parameters
read -ep "${magenta}Point to a source file (e.g. /dir/Image_Name_0001.tif): ${default}" image_name_w_path
    image_name=${image_name_w_path##*/} ##strip away any path from the input
    image_calc_size=$(du -b ${image_name_w_path} | cut -f 1 | head -n 1) # Based on above input, find the file size
    image_suggested_size=$(($image_calc_size - 100000000)) # drop 100 Mb from suggested size since gain noramlized .tif files fluctuate in size ~ 50 Mb or so
    echo "... detected file size $image_calc_size kb ($( du -h --apparent-size ${image_name_w_path} | cut -f 1 | head -n 1 ))"
read -ep "${magenta}Input expected minimum size of a full image (kb): ${default}" -i "${image_suggested_size}" image_size
read -ep "${magenta}Keep motion corrected .MRC files? (e.g. rm /motion_corrected/*.mrc ?): ${default}" -i "no" keep_file_choice
read -ep "${magenta}Suffix for motion corrected images (e.g. For Name_CORRECTED_####.mrc -> CORRECTED): ${default}" -i "Corr" corrected_suffix
read -ep "${magenta}Which microscope (e.g. TF30, F20): ${default}" -i "TF30" microscope
    # my typical settings on HMS microscopes
    case $microscope in
        TF30 ) kV=300; pix_size=0.62; dose=1.196;; # 31000 x mag, default dose
        F20 ) kV=200; pix_size=0.64; dose=0.977;; # 29000 x mag, default dose
    esac
binned_pix_size=$(echo $pix_size | awk '{printf "%4.2f\n",$1*2}') # after MotionCor2, img is 2x binned, this value is required for CTF correction

read -ep "${magenta}Are images gain corrected?: ${default}" -i "no" gain_ref_setting
    case $gain_ref_setting in
        yes ) GAIN_CORRECTED=true ;;
        no ) GAIN_CORRECTED=false
        read -ep "${magenta}  ... point to gain reference (e.g. /dir/SuperRef.mrc): ${default}" -i "SuperRef.mrc" gain_ref_w_path
        read -ep "${magenta}  ... point to defects file (e.g. /dir/defects.txt): ${default}" -i "defects.txt" defects_w_path ;;
    esac

    # Detect gpu setup and assign cards
    gpu_count=$( lspci 2> /dev/null | grep "VGA" | wc -l )
    echo " $gpu_count GPU cards detected. For details during run try: ${yellow}watch -n 1 nvidia-smi${default}"
    # based on GPU count registered, update the suggested variable for the user
    case $gpu_count in
        1 ) suggested_gpu_setting="0";;
        2 ) suggested_gpu_setting="0 1";;
        3 ) suggested_gpu_setting="0 1 2";;
        4 ) suggested_gpu_setting="0 1 2 3";;
        * ) suggested_gpu_setting="0";;
    esac
read -ep "${magenta}MotionCor2 GPU flag to use (e.g. 0 1 2 3; 0 = use first card only): ${default}" -i "$suggested_gpu_setting" gpu_setting

if $VERBOSE; then
    echo
    echo "Variables used..."
    echo "     kV = $kV"
    echo "     pixel size = $pix_size Ang/pix ($binned_pix_size Ang/pix after 2x binning)"
    # echo "     dose = $dose e/pix/frame" # not dose weighting with MotionCor2, so variable not used at the moment
fi


############ Set up destination for motion corrected images
if [ ! -d "./on-the-fly_processing" ]; then
mkdir -v "./on-the-fly_processing"
fi
if [ ! -d "./on-the-fly_processing/CTF" ]; then
mkdir -v "./on-the-fly_processing/CTF"
fi


############ Sanity check
files_selected=$( ls -l ${image_name%_*}*${image_name##*.} | wc -l )
example_selection=$(ls -b ${image_name%_*}*${image_name##*.} | head -1 | xargs ls -d)
example_output_temp="${example_selection%_*}"_"${corrected_suffix}"_"${example_selection##*_}" # needed to easily remove the .tif and replace it with .mrc in the next line
example_output="${example_output_temp%%.*}.gif"
echo
printf "Files of the form: ${cyan}${example_selection}${default} (currently ${cyan}${files_selected}${default} present) will be sent for motion correction \n      e.g.     ${cyan}${example_selection}${default} -> ./on-the-fly_processing/${cyan}"${example_output}"${default} %s\n Script will continuously look for new files as they appear, terminate loop with ${red}Ctrl+C${default} \n"

read -p ">> Proceed? ${magenta}" userinput
echo "${default}"

if [ "$userinput" != "y" ] && [ "$userinput" != "yes" ] && [ "$userinput" != "Y" ] && [ "$userinput" != "Yes" ]; then
  echo "${red}Terminating script.${default}" ; exit
fi

## Set a trap to terminate running loops (SIGINT) and processes (SIGTERM) with control+C even during an active dosefgpu run
trap "echo; rm $image_suggested_size; echo '${red}Script terminated by user.${default}'; exit;" SIGINT SIGTERM
## Automatically terminate script on error or undefined variables
set -eu


(printf "${yellow}\n=====================================\n START LOOP \n=====================================\n${default}");
## if not already present, initialize a log file to store all relevant processing data, otherwise just append data into an existing log file
if [ ! -e on-the-fly_data.log ]; then
    touch ./on-the-fly_data.log
    echo "Log file initialized at ${cyan}./on-the-fly_data.log${default}"
    printf "%s %s %s \n" "##" "Motion_corrected_images=" "./on-the-fly_processing/" >> ./on-the-fly_data.log
    printf "%s %s %s \n" "##" "CTF_fit_images=" "./on-the-fly_processing/CTF/" >> ./on-the-fly_data.log
    printf "## \n" >> ./on-the-fly_data.log
    printf "%-38s %-14s %-14s \n" "## Micrograph" "CTF fit(A)" "Avg. dZ (um)" >> ./on-the-fly_data.log
    printf "%-38s %-14s %-14s \n" "## =============================" "==========" "============" >> ./on-the-fly_data.log
fi

############ Begin loop
while sleep 2.5; do

    for mic in *.tif; do

############ Load file size of source file into variable in units of kb
        source_file_size=$(du -b $mic | cut -f 1)
        source_file_size_human=$(du -h $mic | cut -f 1) #human-readable version of file size for reporting later
############ First condition is to test that file size is correct.
        if [ "$source_file_size" > "$image_size" ]; then
############ Manipulate $mic to generate a new iterative variable that includes path and allows for internal changes in name (e.g. ./on-the-fly_processing/Name*####.mrc)
            intermediate_filename="${mic%_*}"_"${corrected_suffix}"_"${mic##*_}"
            # echo $intermediate_filename
            corrected_filename="${intermediate_filename%%.*}.mrc"
            # echo $corrected_filename
            corrected_gif="${intermediate_filename%%.*}.gif"
            # echo $corrected_gif
            current_file=( ./on-the-fly_processing/"${corrected_filename}" );
            # echo $current_file
            corrected_gif_w_path=( ./on-the-fly_processing/"${corrected_gif}" );
            # echo $corrected_gif_w_path

############ At each iteration, test for the presence of the corrected PNG file in the destination folder. If present sets new variable to 0, else 1.
            test_current_file=$([ -e $corrected_gif_w_path ] && echo "0" || echo "1");
############ Use above test to determine if file should be sent for motion correction or not.
            if [ "$test_current_file" != "0" ]; then
                echo
                echo ">> Sending ${magenta}${mic}${default} for motion correction.";

                if $GAIN_CORRECTED;  then
                    time MotionCor2 -InTiff $mic -OutMrc ./on-the-fly_processing/${corrected_filename} -Patch 5 5 -FtBin 2 -Throw 1 -PixSize $pix_size -GPU $gpu_setting > /dev/null 2>&1 ; echo "   ... corrected drift with MotionCor2"
                else
                    time MotionCor2 -InTiff $mic -OutMrc ./on-the-fly_processing/${corrected_filename} -DefectFile $defects_w_path -Gain $gain_ref_w_path -Patch 5 5 -FtBin 2 -Throw 1 -PixSize $pix_size -GPU $gpu_setting > /dev/null 2>&1 ; echo "   ... corrected drift with MotionCor2"
                fi

                corrected_file_no_path=$(cd ./on-the-fly_processing/ ; ls "${corrected_filename}"); #load output file as a single new variable to simplify next line

                e2proc2d.py ./on-the-fly_processing/"${corrected_file_no_path}" ./on-the-fly_processing/${corrected_file_no_path%%.*}.png --meanshrink 3 --process=filter.lowpass.gauss:cutoff_freq=0.2 > /dev/null 2>&1
                convert ./on-the-fly_processing/${corrected_file_no_path%%.*}.png -resize 70% ./on-the-fly_processing/${corrected_file_no_path%%.*}.gif
                rm ./on-the-fly_processing/${corrected_file_no_path%%.*}.png


                # Launch CTFFIND silently with default inputs for F20 setup at HMS
                echo "   ... fitting CTF with CTFFIND"
                ctffind > /dev/null 2>&1 << INPUT
./on-the-fly_processing/${corrected_file_no_path}
./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.mrc
$binned_pix_size
$kV
2
0.07
512
30
5
10000
40000
150
no
no
no
no
no
INPUT

                # Grab CTF fit & defocus data from the CTFFIND output file in the last line
                est_Reso=$(tail -n 1 ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.txt | awk '{printf "%0.1f",$7}') # row 7
                est_dZ_x=$(tail -n 1 ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.txt | awk '{printf "%d",$2}') # row 2
                est_dZ_y=$(tail -n 1 ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.txt | awk '{printf "%d",$3}') # row 3
                # calculate average dZ from x and y directions, then adjust unit to microns
                est_dZ_avg=$(echo "scale=2; ($est_dZ_x+$est_dZ_y)/20000" | bc -l) # dZ in microns, scale=x is how many digits to keep

                # update log file with all relevant parameters
                printf "%-38s %-14s %-14s" "   $corrected_file_no_path" "$est_Reso" "$est_dZ_avg" >> ./on-the-fly_data.log

                # Format CTF diagnostic image into viewable GIF with e2proc2d.py & convert
                e2proc2d.py ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.mrc ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.png > /dev/null 2>&1
                convert ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.png ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.gif
                rm ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.png

                # Print CTF results
                printf "CTF correction of ${cyan}${corrected_file_no_path%.*}_CTF.mrc${default} reaches ${cyan}$est_Reso${default} Angstroms with an average estimated ${cyan}-$est_dZ_avg um${default} defocus\n"

                # throw warnings if calculated CTF values are out of range
                echo $est_Reso |
                awk -v r=${red} '{
                  if ($1 > 9)
                    {
                    printf r" !!! LOW RESOLUTION FIT !!!";
                    printf "*" >> "./on-the-fly_data.log"
                    }
                }'
                echo $est_dZ_avg |
                awk -v r=${red} '{
                  if ($1 > 3.5)
                    {
                    printf r" !!! HIGH DEFOCUS !!!";
                    printf "*" >> "./on-the-fly_data.log"
                    }
                }'
                echo $est_dZ_avg |
                awk -v r=${red} '{
                  if ($1 < 1.0)
                    {
                    printf r" !!! LOW DEFOCUS !!!";
                    printf "*" >> "./on-the-fly_data.log"
                    }
                }'
                # echo $est_dZ_avg | awk -v r=${red} '{if ($1 > 3.25) {printf r" !!! HIGH DEFOCUS !!!"; printf "*" >> "./on-the-fly_processing/on-the-fly_data.log"} }'
                # echo $est_dZ_avg | awk '{if ($1 < 1.0) printf r" !!! LOW DEFOCUS !!!"; printf "*" >> "./on-the-fly_processing/on-the-fly_data.log"} }'
                printf "\n" >> ./on-the-fly_data.log

                # New line and reset output shell color to default
                printf "${default}\n"

                # to save on file space, run a remove motion corrected micrograph cmd unless the user explicitly asks to keep it
                if [ "$keep_file_choice" != "y" ] && [ "$keep_file_choice" != "yes" ] && [ "$keep_file_choice" != "Y" ] && [ "$keep_file_choice" != "Yes" ]; then
                    rm ./on-the-fly_processing/"${corrected_file_no_path}"
                fi
                # clean up CTFFIND results files
                rm ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.mrc
                rm ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF.txt
                rm ./on-the-fly_processing/CTF/${corrected_file_no_path%.*}_CTF_avrot.txt

            else continue # echo "${magenta}${mic}${default} has been motion corrected -> $corrected_gif"
            fi;
############ If file size test fails, report failure and return to loop
else echo "${cyan}${mic}${default} found, but file size incorrect (${source_file_size_human}), skipping..."
        fi; done
############ End loop
done
