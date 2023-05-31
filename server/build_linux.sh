pyinstaller __main__.py -F -p ./ --name EXviewer -i ../build/favicon.ico --add-data "../build:build"
rm -rf build
rm -f EXviewer.spec