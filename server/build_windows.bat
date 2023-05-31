pyinstaller __main__.py -F -p ./ --name EXviewer -i ../build/favicon.ico --add-data "../build;build"
rd build /s /q
del EXviewer.spec