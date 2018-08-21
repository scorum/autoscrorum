#! /bin/bash

#%
#% runner.sh - script for running autoscorum tests and writing results in result.xml file
#%
#% usage: runner.sh <py.test arguments>
#% 
#% where <py.test arguments> in one of standart py.test args and:
#%		--target=TARGET      specify path to scorumd build directory, parent directory, or directly to scorumd binnary(absolute path)
#%		--image=IMAGE        specify image for tests run(default value=='autonode' if image name != 'autonode' target arg will be ignored)
#%		--use-local-image    do not rebuild image(will be rebuilded by default)
#%
#% examples:
#%		./runner.sh --image scorum/release:latest           run tests on latest release image
#%		./runner.sh --target=/home/username/sources/build   run tests on local scorumd binnary(will try to found it in build/programs/scorumd)
#%		./runner.sh -v                                      run tests on local scorumd(should be installed, will try to find it in PATH)
#%

ME=$(basename "${BASH_SOURCE}")

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
	"${PYTHON_BIN}" --version > /dev/null 2>&1 || { Info "Python is not installed"; return 1; }
	version=$("${PYTHON_BIN}" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')

	if [[ "${version}" != "3.5" ]]; then
		Error "Python 3.5 is required to run tests."
		return 1
	fi

	return 0
}

main()
{
	if [[ "${1}" == "" ]]; then
		synopsis
		return 0
	fi

	SetupColors
	SetPythonBin

	RUNNER_PATH=$(cd $(dirname "$0") && pwd)

	if [ $# -eq 0 ]; then
		args="${RUNNER_PATH}"
	else
		args="$@"
	fi

	pipenv run py.test -n `nproc` --pylama --junitxml=result.xml ${args}
	return $?
}

main $@
exit $?
