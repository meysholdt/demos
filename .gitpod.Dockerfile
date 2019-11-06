FROM gitpod/workspace-full

# the prompt in the Bash Terminal should show 'dwave' and not the current user name
RUN { echo && echo "PS1='\[\e]0;dwave \w\a\]\[\033[01;32m\]dwave\[\033[00m\] \[\033[01;34m\]\w\[\033[00m\] \\\$ '" ; } >> /home/gitpod/.bashrc
