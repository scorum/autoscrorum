#!/bin/bash

#% usage: autoscorum.sh <command>
#%
#% where <command> in one of:
#%   -install           install pip, virtualenv and setup autoscorum project
#%   -uninstall         uninstall pip, virtualenv and clean autoscorum project
#%   -use <bash|csh>    switch 'activate' symlink to bash|shell
#%

ME=$(basename "${BASH_SOURCE}")
INSTALL_PATH=$(cd $(dirname ${BASH_SOURCE}) && pwd)

synopsis()
{
	ME=$(basename "${BASH_SOURCE}")
	ME_FULLPATH="$(cd $(dirname ${BASH_SOURCE}) && pwd)/${ME}"

	awk '/^#%/ {print substr($0,3)}' "${ME_FULLPATH}"
}

SetupColors()
{
	if test -t 2 && which tput >/dev/null 2>&1; then
		ncolors=$(tput colors)
		if test -n "$ncolors" && test $ncolors -eq 256; then
			xWarnColor=$(tput setaf 3 && tput setab 0)  # yellow on black
			xErrorColor=$(tput setaf 7 && tput setab 1) # white on red
			xResetColor=$(tput sgr0)
		elif test -n "$ncolors" && test $ncolors -ge 8; then
			xWarnColor=$(tput setf 6 && tput setb 0)  # yellow on black
			xErrorColor=$(tput setf 7 && tput setb 4) # white on red
			xResetColor=$(tput sgr0)
		fi
	fi
}

Info()
{
	echo ":: $(date +%T) : ${1:-unspecified}" >&2
}

Warn()
{
	echo "${xWarnColor}${ME}: $(date +%T) : WARNING: ${1:-unspecified}${xResetColor}" >&2
}

Error()
{
	echo "${xErrorColor}${ME}: $(date +%T) : ERROR: ${1:-unspecified}${xResetColor}" >&2
}

Die()
{
	Error "$1"
	exit ${2:-1}
}

SetPythonBin()
{
	PYTHON_BIN=$(which python3.5)
}

CheckPython()
{
	${PYTHON_BIN} --version > /dev/null 2>&1 || { Info "Python is not installed"; return 1; }
	version=$(${PYTHON_BIN} -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

	if [[ ${version} != "3.5" ]]; then
		Error "Incorrect version of python $version detected. Python 3.5 is required to run autoscorum."
		return 1
	fi

	return 0
}

RemoveRecursively()
{
	directory=$1
	file_mask=$2
	find "$directory" -name "$file_mask" -exec rm -rf {} \; 2> /dev/null
}

clean()
{
	pipenv --rm

	RemoveRecursively "${INSTALL_PATH}/tests" "\*.pyc"
	RemoveRecursively "${INSTALL_PATH}/tests" "__pycache__"

	RemoveRecursively "${INSTALL_PATH}/autoscorum" "\*.pyc"
	RemoveRecursively "${INSTALL_PATH}/autoscorum" "__pycache__"

	rm -rf "${INSTALL_PATH}/autoscorum.egg-info" 2>&1 &> /dev/null
	rm "${INSTALL_PATH}/result.xml" 2>&1 &> /dev/null
}

setup()
{
    PYTHON_BIN=$(which python3.5)
    bRun=1
	Info "Setup autoscorum environment ..."


	[ $bRun -eq 1 ] && { 
		bash -c "pipenv --python python3.5 install" || {
		Error "Could not create virtualenv"; bRun=0; } }

	[ $bRun -eq 1 ] && { 
		bash -c "pipenv run pip install -e ." || {
		Error "Could not install autoscorum"; bRun=0; } }

	if [ ${bRun} -eq 0 ]; then
		Error "Autoscorum installation failed."
		clean
		return 1
	else
		Info "Autoscorum successfuly installed."
		return 0
	fi
}

main()
{
	SetupColors
	SetPythonBin

	CheckPython || return 1

	if [[ "${1}" == "" ]]; then
		synopsis
		return 0
	fi

	case "${1}" in
		--install)
			clean
			setup
			return $?
			;;
		
		--uninstall)
		    clean
			return $?
			;;

		*)
			synopsis
			return 0
			;;
	esac

	return 0
}

main $1 $2
exit $?
