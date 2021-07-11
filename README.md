# iFirmware-Toolkit v1.0-0121b
Download and manage firmwares for all Apple devices such as iPhone, iPad, iPod, AppleTV, and more.

<img src=".\\resources/01.png" alt="logo" width="800" hieght="800"/>

iFTK runs only on Windows. It's currently not fully compatible on other operating systems.

This project is using [IPSW](https://ipsw.me) API v4. The API part is handled by a server to speed things up. Data pulled from the API is stored in separate database files and then hosted to be used by iFTK. The server checks for updates periodically, and updates database files whenever an update is available for any firmware. 

## Installation

- You will need to download and install the latest version of [Anaconda](https://www.anaconda.com/).
- Initialize `cmd.exe` or anything of your choice using Anaconda Prompt - `conda init cmd.exe`
- Navigate into the directory where you downloaded iFTK and type in the following:
```batch
conda activate base
```
- Download all requirements using pip:
```python
pip install -r requirements.txt
```
- Finally, run `python iFTK.py` 

The `.hosts` file contains server information and is managed during GET requests when downloading updates. In case there is any update to this file,
it will be updated here.

```json
{
    "Server1": "http://li2194-245.members.linode.com:61983"
}
```
## Credits

<div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>
