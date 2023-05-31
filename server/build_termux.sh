pyinstaller __main__.py -F -p ./ --name EXviewer -i ../build/favicon.ico --add-data "../build:build" --add-data "../termux-extend-libs:./"
rm -rf build
rm -f EXviewer.spec