#!/bin/bash
DEBUG=1
GREEN="\e[33;92;1m"
RED="\e[33;91;1m"
YELLOW="\e[33;1m"
C="\e[0m "
# Get file name
if [[ -z $1 ]];then
  echo "Insert log file name:"
  read LOGFILE
  if [[ "$LOGFILE" == "q" || "$LOGFILE" == "Q" ]]; then
    exit 0
  fi
else
  LOGFILE=$1
fi
# If provided serial number oly
if [[ ${#LOGFILE} -eq 12 || ${#LOGFILE} -eq 14 ]]; then
  RUNS=$(cat *.mlnx | grep $LOGFILE)
  NUM=$(printf '%s\n' "$RUNS" | wc -l)
  if [[ $NUM -gt 1 ]]; then
    echo "Multiple runs with this serial:"
    printf '%s\n' "$RUNS" | nl
    read -p "Select one: " SEL_RUN
    if [[ $SEL_RUN -gt $NUM ]]; then
      exit 0
    else
      RUNS_DATA=$(ls -tr | grep $LOGFILE)
      LOGFILE=$(printf '%s\n' "$RUNS_DATA" | sed -n "${SEL_RUN}p")
    fi
  else
    LOGFILE=$(ls | grep $LOGFILE)
    [[ $DEBUG -eq 1 ]] && echo "LOG: "$LOGFILE
  fi
fi
# If provided file with images
if [[ "$LOGFILE" == *"IMG"* ]]; then
  IMGTAR=$LOGFILE
  [[ $DEBUG -eq 1 ]] && echo "Provided file with images: "$IMGTAR
else
  if [[ "$LOGFILE" == "flex"* ]]; then
    # file with run info (*.data)
    IMGTAR=$(less -r $LOGFILE | grep HD_CAM_LOG | grep -o '/usr/log[^ ]*')
  else
    # log file
    IMGTAR=$(less -r $LOGFILE | grep Destination | grep -o '/usr/log[^ ]*')
  fi
  [[ $DEBUG -eq 1 ]] && echo "img tar archive: "$IMGTAR
fi
#OUTDIR=$(echo "$IMGTAR" | sed 's#.*/\([^/]*\)\.dat\.gz$#\1#')
basename="${IMGTAR##*/}"          # get only file name
[[ $DEBUG -eq 1 ]] && echo "basename: "$basename
if [[ $basename == "" ]]; then
  exit 1
fi
NAMEDIR="${basename%.gz}"  # cut suffix .dat.gz
OUTDIR="/tmp/${NAMEDIR}"
[[ $DEBUG -eq 1 ]] && echo "Out dir: "$OUTDIR
mkdir $OUTDIR
[[ $DEBUG -eq 1 ]] && echo "tar -zxf $IMGTAR -C $OUTDIR"
tar -zxf $IMGTAR -C $OUTDIR
if [ "$?" != "0" ];then
  echo "Fail to extract archive"
  exit 1
fi
cp /usr/flexfs/users/leskov/html/led.html.head $OUTDIR/led.html
if [ "$?" != "0" ];then
  echo "Fail to copy html file"
  exit 1
fi
ls -tr $OUTDIR | grep ".jpg"  | awk '{printf "\"%s\",",$0}' | sed 's/,$//' >>$OUTDIR/led.html
echo -e "    ];\ndocument.title = '$basename';" >>$OUTDIR/led.html
cat /usr/flexfs/users/leskov/html/led.html.end >>$OUTDIR/led.html
if [ "$?" != "0" ];then
  echo "Fail to copy html file"
  exit 1
fi
if [[ -n "$SSH_CONNECTION" || -n "$SSH_CLIENT" ]]; then
    cp -r $OUTDIR /var/www/html/
    echo -e "Navigate to $RED http://192.168.10.10/$NAMEDIR/led.html$C in your browser"
else
    firefox $OUTDIR/led.html >/dev/null 2>&1
fi
echo "Press enter to close script"
read
rm -r $OUTDIR
