#!/bin/sh
echo 
mkdir .prover
cd .prover

echo "download tar"
wget https://www.cs.unm.edu/~mccune/prover9/download/LADR-2009-11A.tar.gz
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
cp -r LADR-2009-11A/* .

echo "clean up"
rm -r LADR-2009-11A
rm LADR-2009-11A.tar.gz