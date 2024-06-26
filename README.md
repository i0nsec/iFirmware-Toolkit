# iFirmware-Toolkit v3.9-0306
Download and manage any firmware for all Apple devices such as iPhone, iPad, iPod, AppleTV, and more.

<img src=".\\UI/app.png" alt="logo" width="700" hieght="700"/>

iFTK runs only on Windows. It's currently not fully compatible on other operating systems.

This project is using [IPSW.me](https://ipsw.me) API v4. The API part is handled by a server to speed things up. Data pulled from the API is stored in separate database files and then hosted in GitHub. The server checks for updates periodically, and updates database files whenever an update is available for any firmware. iFTK Repo [iFTK-Updates](https://github.com/i0nsec/iFTK-Updates)

## Installation

- Download and install the latest version of [Anaconda](https://www.anaconda.com/).
- Initialize `cmd.exe` or anything of your choice using Anaconda Prompt
- Open Anaconda Prompt and type in the following:
```
conda init cmd.exe
```
- Create a new environment:
```
conda create --name dev python=3.11.0
```
- Navigate into the directory where you downloaded iFTK and type in the following:
```
conda activate dev
```
- Unzip and install `etc/pyqt-stylesheets-master.zip`
```
python setup.py build
python setup.py install
```
- Install requirements:
```
pip install -r requirements.txt
```
- Finally, run `python iFTK.py` 

The `.hosts` file contains server information and is managed during GET requests when downloading updates. In case there is any update to this file,
it will be updated here.

```json
{
    "host_address": "https://raw.githubusercontent.com"
}
```
## Credits

<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>
