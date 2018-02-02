#! /bin/bash

#%
#% runner.sh - script for running autoscorum tests and writing results in result.xml file
#%
#% usage: runner.sh <py.test arguments>
#%

ME=$(basename "${BASH_SOURCE}")

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
	PYTHON_BIN=$(which python3.6)
}

CheckPython()
{
	"${PYTHON_BIN}" --version > /dev/null 2>&1 || { Info "Python is not installed"; return 1; }
	version=$("${PYTHON_BIN}" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

	if [[ "${version}" != "3.6" ]]; then
		Error "Incorrect version of python $version detected. Python 3.6 is required to run tests."
		return 1
	fi

	return 0
}

main()
{
	SetupColors
	SetPythonBin

	RUNNER_PATH=$(cd $(dirname "$0") && pwd)

	if [ $# -eq 0 ]; then
		args="${RUNNER_PATH}"
	else
		args="$@"
	fi

	pipenv run py.test --pylama --junitxml=result.xml ${args}
	return $?
}

main $@
exit $?
