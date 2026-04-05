import PyInstaller.__main__
import os

if __name__ == '__main__':
    PyInstaller.__main__.run([
        'src/infini_think/app/launcher.py',  
        '--name=infini-think',     
        '--onedir',                
        '--windowed',              
        '--icon=infini_think.ico',
        '--add-data=src/infini_think/assets;infini_think/assets',
        '--noconfirm',            
        '--clean'                 
    ])
