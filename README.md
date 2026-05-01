# GogolFlex
GogolFlex is a simple search engine, working with Python 3 and React, and running in Docker.

# Installation
> [!WARNING]
> You need to have Docker installed to setup GogolFlex

## Windows
- Download `gogolflex-setup.exe` in releases & place the file in a working directory.
- Execute `gogolflex-setup.exe`.
- Define the admin's password (password to access the administrator panel).
- Define the database's password.
- You can quit `gogolflex-setup.exe` once the containers are running
## Linux
- Go in a working directory
- Download `gogolflex-linux` with this command :
```commandline
wget https://github.com/Jzombi-le-codeur/GogolFlex/releases/download/v1.0.0/gogolflex-linux
```
- Execute `gogolflex-linux` with these commands :
```commandline
chmod u+x gogolflex-linux
./gogolflex-linux
```
- Define the admin's password (password to access the administrator panel).
- Define the database's password.
- You can quit `gogolflex-setup.exe` once the containers are running.

# Run
## Docker Desktop
- Launch Docker Desktop
- Go into `Containers` section
- Launch `gogolflex`
## Windows (terminal)
- Open a terminal & go in the working directory
- Enter this command :
```commandline
docker compose up
```
## Linux
- Open a terminal & go in the working directory
- Enter this command :
```commandline
sudo docker compose up
```