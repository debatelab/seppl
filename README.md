# seppl
AI-Powered E-Learning App for Argument Analysis


```sh
# build image (optional)
docker build -t seppl:latest .

# run app
docker run -ti --rm --expose 8051 --network host seppl:latest
```

Access docker via bash:

```sh
docker run -ti --rm seppl:latest bash
```