#!/bin/sh

if [ ! -f "./LADR-2009-11A.tar.gz" ]
then
    echo "download tar"
    wget https://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz
else
    echo "archive exists"
fi
ls 

echo "unzip"
tar -xvzf LADR-2009-11A.tar.gz

echo "make"
cd LADR-2009-11A
make all

echo "test installation"
make test1

echo "copy to .prover"
cd ..
mkdir .prover
cp -r LADR-2009-11A/* .prover

echo "clean up"
rm -r LADR-2009-11A
rm LADR-2009-11A.tar.gz