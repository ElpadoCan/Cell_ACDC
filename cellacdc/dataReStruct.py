import collections
import os
import re
import traceback
from functools import partial

import numpy as np
import pandas as pd
import skimage.io
from natsort import natsorted
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QFileDialog

from . import apps, html_utils, myutils, printl, widgets, workers

frame_name_pattern = r'_(day)*(\d+)\.[A-Za-z0-9]+'

def readFilenamePattern(fileName):
    try:
        frameNumber = re.findall(frame_name_pattern, fileName)[0][1]
    except Exception as e:
        frameNumber = None
    
    s = re.sub(frame_name_pattern, '', fileName)

    for i, c in enumerate(s[::-1]):
        if c == '_':
            break
    channelName = s[-i:]
    posName = s[:-i-1]
    return posName, frameNumber, channelName


def _log(mainWin, text):
    mainWin.log(text)

def run(mainWin):
    items = (
        'Multiple files, one for each time-point', 
    )
    selectHowWin = apps.QDialogCombobox(
        'Select how files are structured', items,
        'Select <b>how files are structured</b>',
        CbLabel='', parent=mainWin
    )
    selectHowWin.exec_()
    if selectHowWin.cancel:
        return False
    
    mainWin.log(f'[Data Re-Struct] Selected file structure = "{selectHowWin.selectedItemText}"')

    msg = widgets.myMessageBox(showCentered=False, wrapText=False)
    txt = html_utils.paragraph("""
        Put all of the raw image files from the <b>same experiment</b><br> 
        into an <b>empty folder</b> before closing this dialogue.<br><br>

        Note that there should be <b>no other files</b> in this folder.
    """
    )
    msg.information(
        mainWin, 'Microscopy files location', txt, 
        buttonsTexts=('Cancel', 'Done')
    )
    if msg.cancel:
        return False
    
    mainWin.log(
        '[Data Re-Struct] Asking to select the folder that contains the image files...'
    )
    MostRecentPath = myutils.getMostRecentPath()
    rootFolderPath = QFileDialog.getExistingDirectory(
        mainWin.progressWin, 'Select folder containing the image files', 
        MostRecentPath)
    myutils.addToRecentPaths(rootFolderPath)
    if not rootFolderPath:
        return False
    
    mainWin.log(
        '[Data Re-Struct] Asking in which folder to save the images files...'
    )
    dstFolderPath = QFileDialog.getExistingDirectory(
        mainWin.progressWin, 
        'Select the folder in which to save the images files',
        rootFolderPath
    )
    myutils.addToRecentPaths(dstFolderPath)
    if not rootFolderPath:
        return False
    
    mainWin.log('[Data Re-Struct] Checking file format of loaded files...')
    validFilenames = checkFileFormat(rootFolderPath, mainWin)
    if not validFilenames:
        return False

    if selectHowWin.selectedItemIdx == 0:
        s = _run_multi_files_timepoints(
            mainWin, validFilenames, rootFolderPath, dstFolderPath
        )
        return s
    
    return True

def checkFileFormat(folderPath, mainWin):
    ls = natsorted(myutils.listdir(folderPath))
    files = [
        filename for filename in ls
        if os.path.isfile(os.path.join(folderPath, filename))
    ]
    all_ext = [
        os.path.splitext(filename)[1] for filename in ls
        if os.path.isfile(os.path.join(folderPath, filename))
    ]
    counter = collections.Counter(all_ext)
    unique_ext = list(counter.keys())
    is_ext_unique = len(unique_ext) == 1
    most_common_ext, _ = counter.most_common(1)[0]
    if not is_ext_unique:
        msg = widgets.myMessageBox(wrapText=False)
        txt = html_utils.paragraph(
            'The following folder<br><br>'
            f'<code>{folderPath}</code><br><br>'
            'contains <b>files with different file extensions</b> '
            f'(extensions detected: {unique_ext})<br><br>'
            f'However, the most common extension is <b>{most_common_ext}</b>, '
            'do you want to proceed with<br>'
            f'loading only files with extension <b>{most_common_ext}</b>?'
        )
        _, proceedWithMostCommon = msg.warning(
            mainWin, 'Multiple extensions detected', txt,
            buttonsTexts=('Cancel', 'Yes')
        )
        if proceedWithMostCommon == msg.clickedButton:
            files = [
                filename for filename in files
                if os.path.splitext(filename)[1] == most_common_ext
            ]
            otherExt = [ext for ext in unique_ext if ext != most_common_ext]
        else:
            return []

    return files

def saveTiff(filePath, data, waitCond):
    myutils.imagej_tiffwriter(filePath, data, None, 1, 1)
    waitCond.wakeAll()
    del data

def _run_multi_files_timepoints(
        mainWin, validFilenames, rootFolderPath, dstFolderPath
    ):
    sampleFilename = validFilenames[0]

    win = apps.MultiTimePointFilePattern(
        sampleFilename, rootFolderPath, readPatternFunc=readFilenamePattern
    )
    win.exec_()
    if win.cancel:
        return False
    
    mainWin.thread = QThread()
    mainWin.restructWorker = workers.RestructMultiTimepointsWorker(
        win.allChannels, frame_name_pattern, win.basename, validFilenames,
        rootFolderPath, dstFolderPath, segmFolderPath=win.segmFolderPath
    )
    mainWin.restructWorker.moveToThread(mainWin.thread)
    mainWin.restructWorker.signals.finished.connect(mainWin.thread.quit)
    mainWin.restructWorker.signals.finished.connect(
        mainWin.restructWorker.deleteLater
    )
    mainWin.thread.finished.connect(mainWin.thread.deleteLater)

    # Custom signals
    mainWin.restructWorker.signals.critical.connect(mainWin.workerCritical)
    mainWin.restructWorker.signals.finished.connect(mainWin.workerFinished)
    mainWin.restructWorker.signals.progress.connect(mainWin.workerProgress)
    mainWin.restructWorker.signals.initProgressBar.connect(
        mainWin.workerInitProgressbar
    )
    mainWin.restructWorker.signals.progressBar.connect(
        mainWin.workerUpdateProgressbar
    )
    mainWin.restructWorker.sigSaveTiff.connect(saveTiff)

    mainWin.thread.started.connect(mainWin.restructWorker.run)
    mainWin.thread.start()

    return True