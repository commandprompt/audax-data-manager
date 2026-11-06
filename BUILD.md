# Building PgManage desktop app

The **deploy** sub-directory of this project has a number of helper scripts which should be used to build the application release binary files.

The build process is similar for all platforms. Here is a brief description of how it works:

 - The build script clones the git repository into a temporary dir.
 - The necessary app and build dependencies are installed. Application is
   being built.
 - The back-end service is packaged into a self-contained
   binary(or a directory structure) by pyInstaller.
 - The resulting files
   are then collected and packed into the distributable binary file
   (.appimage .dmg or .exe).

## Linux AppImage

Here is the list of steps involved in the build process:

cd ./deploy/linux
run ./build_images.sh to produce the Docker container which will be used as a build environment
once build_images.sh completes run ./deploy.sh script.
```
./deploy.sh [pgmanage_version] [branch_name] [debug_mode]
```
- `pgmanage_version`(*optional*): The version number that will be added to bundle.
If not provided, the script defaults to the last version tag from Git repository.
- `branch_name`(*optional*): The Git branch to build from.If not provided, the script defaults to the `dev` branch.
- `debug_mode`(*optional*): If debug `true`, then nwjs-sdk will be used. Defaults to `false`.

This will will start the build process inside of a Docker container.

**Note:** it is not necessary to run build_images.sh each time. This script should be re-run however if changes are made to the app build scripts themselves (entrypoint.sh etc).

The build process takes about 2 minutes to complete. Once deploy.sh completes the current directory should contain a freshly built .appimage file.

## Linux Snap

The snap is made from the .deb file that deploy.sh builds. Snapcraft and LXD must be installed.

```
cd ./deploy/linux
./deploy.sh [pgmanage_version]
./build_snap.sh [pgmanage_version]
```

The current directory then contains the audaxdm_[pgmanage_version]_amd64.snap file. To install it locally:
```
sudo snap install --dangerous audaxdm_[pgmanage_version]_amd64.snap
```



## Mac OS .dmg

TODO



## Windows .exe installer

The build should be done on Windows 10 x86_64 OS.
The following software should be installed prior to runnig the build script:
Official Python 3.11.9 windows release

 - Cygwin
 - NSIS
 - ResourceHacker
 - Visual Studio Build Tools 2022
 - Microsoft Visual C++ Redistributable
 - Git

The **windows/deploy.sh** script assumes that the software mentioned above is installed in default locations.

Here are the steps necessary to produce windows build:

 - open cygwin console, clone/pull pgmanage project source code
 - cd to $pgmanage_root/deploy/windows
 - run ./deploy.sh the build process should start
 - at the end of build process the NSIS GUI window should open
 -  once NSIS installer build completes you can click the "Test
   Installer" button to do a test install or choose to exit NSIS.

The current directory should contain the freshly built installer executable file.
