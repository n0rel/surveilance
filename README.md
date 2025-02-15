# NVR Backend
A small NVR backend which monitors objects in security cameras (or any camera!).

## Deployment

### MiNiFi
MiNiFi is used to 

Build an official image of MiNiFi. In order to do so, follow the instructions in the `apache/nifi-minifi-cpp` repository.
Built with extensions: AWS & Elasticsearch

Two files need to be under the `mediamtx/` directory:
    1.  File named `bootstrap.conf`
        The file needs to be one line with a nifi compatible key that encrypts/decrypts secrets:
        ```
        nifi.bootstrap.sensitive.properties.key=
        ```
    2.  File named `minifi-config.yml`
        The file describes the flow of the MiNiFi instance. Make sure to edit the variables to match your deployment environment

### Detector
WARNING: Docker image created size is huge (20gb)
A TensorRT optimized model (`model.engine` file) needs to be under the `detector-worker/` directory.
The model needs to obey the following properties:
* 8 batches


### MediaMTX
A `mediamtx.yml` file needs to be under the `mediamtx/` directory.
Make sure to add all your cameras under `paths:` because the Detector queries the MediaMTX API to get the paths
