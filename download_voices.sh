#!/bin/bash

set -e

downloads=""
# downloads="$downloads dev-clean"
# downloads="$downloads dev-other"
downloads="$downloads train-other-500"

mkdir -p zips
cd zips
for f in $downloads; do
  if [ -e $f.tar.gz ]; then
    echo "Found $f"
  else
    wget http://www.openslr.org/resources/12/$f.tar.gz
  fi
done
cd ..

mkdir -p voices
cd voices
for f in $downloads; do
  if [ ! -e $f ]; then
    echo "Unpacking $f"
    mkdir $f
    cd $f
    tar xf ../../zips/$f.tar.gz
    cd ..
  fi
done

for f in `find . -iname "*.flac"`; do
  part=`echo $f | sed 's/flac$/wav/'`
  echo $part
  if [ ! -e $part ]; then
    ffmpeg -loglevel panic -i $f -c:a pcm_s16le -ar 16000 -ac 1 $part
  fi
done
cd ..

python prep/main.py inventory
