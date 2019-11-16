# orhelper
Python module to connect with OpenRocket and do some headless magic

## Installation

**Prerequisites**:
Java JDK 1.8 works in my case, but OpenRocket recommends 1.7.
Python 3.6+ and Pipenv for dependency management.

**Steps**

Get OpenRocket jar file or set variable CLASSPATH which points to your OpenRocket jar
```
wget https://github.com/openrocket/openrocket/releases/download/release-15.03/OpenRocket-15.03.jar
```

Setup `.env` file to include JAVA_HOME
```
JDK_HOME=/usr/lib/jvm/java-8-openjdk-amd64
JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# default
CLASSPATH=OpenRocket-15.03.jar
```

Get inside venv
```
pipenv install --skip-lock
pipenv shell
```

Run orhelper.py inside venv, _no errors should pop-up_
```
python orhelper.py
```

**Troubleshooting**
You need to compile dependencies like JPype1 with correct envs. Try inside venv running bare pip
```
pip install JPype1 --force-reinstall --no-cache-dir
```

## Additional info
Thats all what I found and fixed regarding this project.
http://wiki.openrocket.info/Scripting_with_Python_and_JPype proved to be outdated.
There is main issue regarding this topic which was active while researching this https://github.com/openrocket/openrocket/issues/532.
