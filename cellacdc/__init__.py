import sys
import os
import inspect
import traceback
from datetime import datetime
from pprint import pprint

from functools import wraps
from . import html_utils

def printl(*objects, pretty=False, is_decorator=False, **kwargs):
    # Copy current stdout, reset to default __stdout__ and then restore current
    current_stdout = sys.stdout
    sys.stdout = sys.__stdout__
    timestap = datetime.now().strftime('%H:%M:%S')
    currentframe = inspect.currentframe()
    outerframes = inspect.getouterframes(currentframe)
    idx = 2 if is_decorator else 1
    callingframe = outerframes[idx].frame
    callingframe_info = inspect.getframeinfo(callingframe)
    filpath = callingframe_info.filename
    filename = os.path.basename(filpath)
    print_func = pprint if pretty else print
    print('*'*30)
    print(f'{timestap} - File "{filename}", line {callingframe_info.lineno}:')
    print_func(*objects, **kwargs)
    print('='*30)
    sys.stdout = current_stdout

cellacdc_path = os.path.dirname(os.path.abspath(__file__))
parent_path = os.path.dirname(cellacdc_path)
data_path = os.path.join(parent_path, 'data')
temp_path = os.path.join(cellacdc_path, 'temp')
settings_csv_path = os.path.join(temp_path, 'settings.csv')
user_manual_url = 'https://github.com/SchmollerLab/Cell_ACDC/blob/main/UserManual/Cell-ACDC_User_Manual.pdf'

# Use to get the acdc_output file name from `segm_filename` as 
# `m = re.sub(segm_re_pattern, '_acdc_output', segm_filename)`
segm_re_pattern = r'_segm(?!.*_segm)'

if not os.path.exists(temp_path):
    os.makedirs(temp_path)

try:
    from setuptools_scm import get_version
    __version__ = get_version(root='..', relative_to=__file__)
except Exception as e:
    try:
        from ._version import version as __version__
    except ImportError:
        __version__ = "not-installed"

__author__ = 'Francesco Padovani and Benedikt Mairhoermann'

cite_url = 'https://bmcbiol.biomedcentral.com/articles/10.1186/s12915-022-01372-6'
issues_url = 'https://github.com/SchmollerLab/Cell_ACDC/issues'

# Initialize variables that need to be globally accessible
base_cca_df = {
    'cell_cycle_stage': 'G1',
    'generation_num': 2,
    'relative_ID': -1,
    'relationship': 'mother',
    'emerg_frame_i': -1,
    'division_frame_i': -1,
    'is_history_known': False,
    'corrected_assignment': False
}

base_acdc_df = {
    'is_cell_dead': False,
    'is_cell_excluded': False,
    'was_manually_edited': 0
}

is_linux = sys.platform.startswith('linux')
is_mac = sys.platform == 'darwin'
is_win = sys.platform.startswith("win")
is_win64 = (is_win and (os.environ["PROCESSOR_ARCHITECTURE"] == "AMD64"))

yeaz_weights_filenames = [
    'unet_weights_batchsize_25_Nepochs_100_SJR0_10.hdf5',
    'weights_budding_BF_multilab_0_1.hdf5'
]

yeastmate_weights_filenames = [
    'yeastmate_advanced.yaml',
    'yeastmate_weights.pth',
    'yeastmate.yaml'
]

graphLayoutBkgrColor = (235, 235, 235)
darkBkgrColor = [255-v for v in graphLayoutBkgrColor]

def exception_handler(func):
    @wraps(func)
    def inner_function(self, *args, **kwargs):
        try:
            if func.__code__.co_argcount==1 and func.__defaults__ is None:
                result = func(self)
            elif func.__code__.co_argcount>1 and func.__defaults__ is None:
                result = func(self, *args)
            else:
                result = func(self, *args, **kwargs)
        except Exception as e:
            try:
                if self.progressWin is not None:
                    self.progressWin.workerFinished = True
                    self.progressWin.close()
            except AttributeError:
                pass
            from . import widgets
            result = None
            traceback_str = traceback.format_exc()
            if hasattr(self, 'logger'):
                self.logger.exception(traceback_str)
            else:
                printl(traceback_str)
            msg = widgets.myMessageBox(wrapText=False, showCentered=False)
            if hasattr(self, 'logs_path'):
                msg.addShowInFileManagerButton(
                    self.logs_path, txt='Show log file...'
                )
            if not hasattr(self, 'log_path'):
                log_path = 'NULL'
            else:
                log_path = self.log_path
            msg.setDetailedText(traceback_str, visible=True)
            href = f'<a href="{issues_url}">GitHub page</a>'
            err_msg = html_utils.paragraph(f"""
                Error in function <code>{func.__name__}</code>.<br><br>
                More details below or in the terminal/console.<br><br>
                Note that the <b>error details</b> from this session are
                also <b>saved in the following log file</b>:
                <br><br>
                <code>{log_path}</code>
                <br><br>
                You can <b>report</b> this error by opening an issue
                on our {href}.<br><br>
                Please <b>send the log file</b> when reporting a bug, thanks!
            """)

            msg.critical(self, 'Critical error', err_msg)
            self.is_error_state = True
        return result
    return inner_function