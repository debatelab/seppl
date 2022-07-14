# seppl
AI-Powered E-Learning App for Argument Analysis


```sh
# update requirements (optional)
poetry export -f requirements.txt --output requirements.txt --without-hashes

# build image (optional)
docker build -t seppl:latest .

# run app
docker run -ti --rm --gpus all --expose 8051 --network host seppl:latest
```

Access docker via bash:

```sh
docker run -ti --rm --gpus all da2-inspector:latest bash
```