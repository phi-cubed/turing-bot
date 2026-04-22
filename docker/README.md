# Turing @ DMF: containerization using Docker

## 1. Basic configuration
1. Install `docker` following the instructions in the official documentation: [Debian `amd64`](https://docs.docker.com/engine/install/debian/#install-using-the-repository), [Fedora `amd64`](https://docs.docker.com/engine/install/fedora/#install-using-the-repository), [Raspberry Pi `armhf`](https://docs.docker.com/engine/install/raspberry-pi-os/#install-using-the-repository), [Ubuntu `amd64`](https://docs.docker.com/engine/install/ubuntu/#install-using-the-repository).

2. Pull the **Turing @ DMF** docker image
```
docker pull ghcr.io/dmf-unicatt/turing-dmf:latest
```

3. Run a new docker container
```
docker run -p 80:80 ghcr.io/dmf-unicatt/turing-dmf:latest
```
**Turing** will be available at `http://localhost`. Furthermore, the terminal will display (towards the end of a long initialization message) the username and password of the administrator account, which can be subsequently changed through the web interface.


## 2. Advanced configuration
The basic configuration is useful for local testing, but should not be used in production because, for example, the database is not shared between different runs.

### 2.1. Set up the host server

1. Install `docker` as in the basic configuration.

2. Clone the **Turing @ DMF** repository as follows:
```
git clone https://github.com/dmf-unicatt/turing-dmf.git
```

### 2.2. Set up the docker container

1. All the following instructions are supposed to be run in the `turing-dmf/docker` directory:
```
cd turing-dmf/docker
```

2. Create a docker volume that will contain the database:
```
./create_volume.sh
```

3. Create a `ghcr.io/dmf-unicatt/turing-dmf:latest` docker image based on the current **Turing @ DMF** repository:
```
./create_image.sh
```

4. Create a docker container based on the newly created `ghcr.io/dmf-unicatt/turing-dmf:latest` docker image:
```
./create_container.sh
```

5. Database is created upon the first run of the container with
```
./start_container.sh
```
The terminal will display (towards the end of a long initialization message) the username and password of the administrator account, which can be subsequently changed through the web interface.

### 2.3. Run the docker container

1. All the following instructions are supposed to be run in the `turing-dmf/docker` directory:
```
cd turing-dmf/docker
```

2. Start the container, including the `django` server:
```
./start_container.sh
```
**Turing** will be available at `http://host-server`.

3. Attach a terminal to the running docker container
```
./attach_terminal.sh
```

4. Explore the database volume with
```
./explore_volume.sh
```

5. Stop the running docker container
```
./stop_container.sh
```

### 2.4. Tips and tricks

1. The above scripts internally use three hidden files `.container_id`, `.network_id` and `.volume_id` to store the result of running the above commands. You may protect those files from accidental deletion by running
```
sudo ./prevent_accidental_deletion.sh
```

2. If you want to create a new container, make sure to stop the old one (if it were running), and remove the file `.container_id`. Note that, to prevent data loss, this does not delete the old container itself, it only disables it from being used by the above scripts.

3. If you want to create a new volume, remove the file `.volume_id`. Note that, to prevent data loss, this does not delete the old volume itself, it only disables it from being used by the above scripts.
