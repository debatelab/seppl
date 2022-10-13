# seppl
AI-Powered E-Learning App for Argument Analysis


```sh
# build image (optional)
docker build -t seppl:latest .

# run app
docker run -ti --rm --expose 8080 --network host seppl:latest
```

Access docker via bash:

```sh
docker run -ti --rm seppl:latest bash
```


### Prover9

> In compiling with gcc 7.4.0, we get error:
> 
> gcc  -O -Wall -lm -o prover9 prover9.o index_lits.o forward_subsume.o demodulate.o pred_elim.o unfold.o semantics.o giv_select.o white_black.o actions.o search.o utilities.o provers.o foffer.o ../ladr/libladr.a
> search.o: In function `search':
> search.c:(.text+0x6654): undefined reference to `round'
> 
> This is because the make directive is not of the correct (or new) format:
> 
> prover9: prover9.o $(OBJECTS)
> 	$(CC) $(CFLAGS) -lm -o prover9 prover9.o $(OBJECTS) ../ladr/libladr.a
> 
> It should be:
> 
> prover9: prover9.o $(OBJECTS)
> 	$(CC) $(CFLAGS) -o prover9 prover9.o $(OBJECTS) ../ladr/libladr.a -lm
> 
> There are also unused variables such as:
> mindex.c:650:11: warning: variable ‘tr’ set but not used [-Wunused-but-set-variable]
>      Trail tr;
> 
> These defects can be fixed easily.