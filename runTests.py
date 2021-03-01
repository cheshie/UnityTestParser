from subprocess import Popen
import argparse
from os.path import join, splitext, exists
from clear_screen import clear
import xml.etree.ElementTree as ET
from datetime import datetime
from re import findall
from time import sleep

### Original command - example of running tests for example project on Unity 2018.3.2f1
# "C:\Program Files\Unity\Hub\Editor\2018.3.2f1\Editor\Unity.exe" -batchmode -projectPath "C:\Users\PrzemyslawSamsel\OneDrive - Apptimia Sp. z o.o\Documents\Crashteroids-project-files\Crashteroids\Crashteroids Starter" -runTests -testPlatform playmode

# Consts
# docs: https://docs.unity3d.com/530/Documentation/Manual/testing-editortestsrunner.html
hub_path_windows = r'C:\Program Files\Unity\Hub\Editor'

# Separators for test case and testsuite
septc = "{:-^50}".format('')
septs = "{:#^50}".format('')

# Test run aligns and header
algl  = "{:<17}" # align left
algr  = "{:>29}" # align right
alght = "\n{:*^50}\n" # align header top
alghb = "{:-^50}"     # align header bottom
trheader = " test-run " # test-run header

# Test run attributes
trattrs = [
        ("TC Count:", "testcasecount"),
        ("TC Passed:", "passed"),
        ("TC Failed:", "failed"),
        ("Duration:", "duration"),
]

# Test Suite params - header, aligns, attrs
tsheader = " test-suites "
algtsht  = "\n{:*^50}\n" # Align test suite header top
algtshb  = "{:-^50}" # -/- bottom
tsalgl   = "{:<19}"  # test suite align left
tsalgr   = "{:>31}"  # test suite align right
# Attribute's names 
tsattrs  = [
        ("Test name:", 'fullname'),
        ("Testcase count:", 'testcasecount'),
        ("Result:", 'result'),
        ("Start time:", 'start-time'),
        ("End time:", 'end-time'),
        ("Duration:", 'duration'),
]
# Test Case params - header
tcheader = " test cases "
tcalgt   = "{:#^50}"
tcalgl   = "{:<12}"
# Test Case tags
tcattrs = [
        ("TestID", "id"), 
        ("Name", "fullname"),
        ("Method", "methodname"),
        ("Duration", "duration"),
        ("Asserts", "asserts"),
        ("Result", "result")
]

# Handling TestCase failure
fail   = "Failed"
reason = "Reason:"
failtag = "failure"
msgtag = "message"
stacktrace = "Stacktrace:"
stacktracetag = "stack-trace"
newlinefillregx = "(?s).{,50}" # newline every 50 chars

# Executing Unit Tests
testwait = "[*] Executing tests in Unity [ "
testwaitanim = ['-', '\\', '|', '/']
testwaitend = " ]"

# Coloring output in terminal
# Green keywords
grn_kwds = ['Passed', 'passed']
red_kwds = ['Failed', 'failed']
blu_kwds = ['test-run', 'test-suites', 'test cases']
# Green beginning and end escape codes
grn_cd = '\x1b[6;30;42m'
red_cd = '\x1b[0;30;41m'
blu_cd = '\x1b[0;32;44m'
endcode = '\x1b[0m'
kwds = list(zip(grn_kwds, [grn_cd] * len(grn_kwds))) +\
       list(zip(red_kwds, [red_cd] * len(red_kwds))) +\
       list(zip(blu_kwds, [blu_cd] * len(blu_kwds)))


class UnityTestParser:
  def __init__(self):
    self.report = ""
    self.ParseArgs()

  def ParseArgs(self):
    parser = argparse.ArgumentParser(description=\
            'Automate Unity Testing from commandline')
    parser.add_argument('-v', '--unityver', type=str, 
            default='2018.3.2f1', help='Version of Unity')
    parser.add_argument('-b', '--unitybasedir', type=str,
            default=hub_path_windows, help='Base dir of all versions of Unity')
    parser.add_argument('-p', '--projpath', type=str, 
            help='Full path of project to be tested', required=False) #TODO => test (True)
    parser.add_argument('-t', '--testtype', type=str, 
            default='play', choices=['play, editor'], help='Run either editor or playmode tests')
    parser.add_argument('-o', '--outfile', 
            help='Path to results XML file exported after tests'
                'by Unity. Default location is project folder') # default output file option see below
    parser.add_argument('-f', '--form', type=str,
            default='stdout', choices=['stdout', 'html', 'json'], help="Format of parsed XML. Could"
            "either be sent to stdout or parsed to specific filetype")
    parser.add_argument('--short', action='store_true', help="If present, prints test results as a short summary"
            " (this also includes error messages).")
    parser.add_argument('--nocolor', action='store_false', help='If this option is present, '
    '')
    self.args = parser.parse_args()
    
    # Specyfing arguments passed to Unity in terminal
    # Path to unity executable
    self.args.unity_exec_path = join(self.args.unitybasedir, self.args.unityver, 'Editor', 'Unity.exe')
    # Used to not spawn graphical UI 
    self.args.batcharg = '-batchmode'
    # Project path to be debugged
    self.args.projpatharg = '-projectPath'
    # Arguments passed to specific type of tests
    self.args.test_args = []
    # Output file
    self.args.output = ['-editorTestsResultFile']

    # Test output file - user defined
    if self.args.outfile:
    # Output file for results
      self.args.output += [args.outfile]
    # Test output file - default path (project)
    else:
      # TODO => only testing 
      #self.filename = #"TestResults-637497000092310934.xml" #'TestResults-637496073708155152.xml'
      self.filename = "TestResults-01032021104556.xml" #'TestResults-' + datetime.now().strftime('%d%m%Y%H%M%S') + '.xml' 
      self.args.output += [join(self.args.projpath, self.filename)]
    
    # Run tests in either playmode (chosing playmode platform) or editor tests
    if self.args.testtype == 'play':
      test_type = '-runTests'
      test_platform = '-testPlatform'
      mode = 'playmode'
      self.args.test_args = [test_type, test_platform, mode]
    elif self.args.testtype == 'editor':
      test_type = '-runEditorTests'
      self.args.test_args = [test_type]
  #

  # Run unity exec with proper parameters
  def RunTests(self):
    # Prepare test arguments
    testargs = [
        self.args.unity_exec_path, 
        self.args.batcharg,
        self.args.projpatharg,
        self.args.projpath,
        *self.args.test_args,
        *self.args.output
    ]
    
    # Run tests
    process = Popen(testargs, shell=True)
    
    # Wait for Unity to execute tests and generate XML results
    i = 0
    while not exists(join(self.args.projpath, self.filename)):
      # Print "progress bar"
      print(testwait + testwaitanim[i] + testwaitend)
      i = (i + 1) % len(testwaitanim)
      sleep(0.1)
      clear()
  #

  """
  Pare XML document generated by Unity. In general, structure of this doc is similar to:
  <test-run>
    <test-suite type=TestSuite>
          <test-suite type=Assembly>
            <properties>
            </properties>
            <test-suite type=TestFixture>
                <===# Listing of all test cases #===>
            </test-suite>
            <test-suite type=TestFixture>
                <===# Listing of all test cases #===>
            </test-suite>
                  (...)
          </test-suite>
    </test-suite>
  </test-run>

  This structure is important, bcoz this function looks for any test-suite tags
  with type attribute of value TestFixture, and then it parses all test cases one by one
  """
  def ParseResults(self):
    # Test document root handle
    self.htest = ET.parse(self.args.output[1]).getroot()
    # Test Run (general stats)
    self.parse_tr()
    # Specific Test Suites
    self.parse_ts()
    self.PrintReport()
  #
  
  # Parse Test Cases
  def parse_tcs(self, ts):
    tests = ts.findall("./test-case")
    if not self.args.short: 
      self.out(tcalgt.format(tcheader))
    for test in tests:
      for attr in tcattrs:
        if not self.args.short or fail in test.attrib.values(): 
          self.out(tcalgl.format(f"# {attr[0]}:"), 
                  tcalgl.format(f"{test.attrib[attr[1]]}"))
        # If result equals Failed
        if fail in test.attrib[attr[1]]:
          self.out(reason)
          self.out(test.find(failtag).find(msgtag).text) 
          # Stacktrace is not printed in short mode
          if not self.args.short:
            self.out(stacktrace)
          # Wrapping stacktrace with newline every n chars
            st = test.find(failtag).find(stacktracetag).text
            self.out("\n".join(findall(newlinefillregx, st))[:-1])
      if not self.args.short: 
        self.out(septc)
  #
  
  # Parse Test Run
  def parse_tr(self):
    # Header
    self.out(alght.format(trheader) + alghb.format(''))
    # Attributes of Test Run
    for at in trattrs:
      val = self.htest.attrib[at[1]]
      self.out("* " + algl.format(at[0]), algr.format(val) + " *")
    # Bottom header
    if not self.args.short: 
      self.out(alghb.format('') + alght.format(''), lend="")
  #
  
  # Parse Test Suites
  def parse_ts(self):
    # Header
    self.out(algtsht.format(tsheader) + algtshb.format(''))
    # Test Suites
    for ts in self.htest.findall(".//test-suite[@type='TestFixture']"):
      # Separator between testcases
      if not self.args.short: 
        self.out(septs)
      # Test Suite Attributes
      for at in tsattrs:
        self.out(tsalgl.format(at[0]), tsalgr.format(ts.attrib[at[1]]))
      # If short is not present - print separator
      # If short is present BUT no test case failed - print separator
      # If short is present BUT the result is failed (because any of tc failed) - do not print
      if not self.args.short or self.args.short and fail not in ts.attrib.values():
      # Bottom header of test suite
        self.out(algtshb.format(''))
      # Parse Test Cases
    self.parse_tcs(ts)
  #
  
  # Add next lines to report string
  def out(self, *printargs, lend='\n'):
    for arg in printargs:
      self.report += arg
    self.report += lend
  #
  
  # Print string to either stdout or a file
  def PrintReport(self):
    if self.args.form == 'stdout':
      # Insert color escape codes in report
      if self.args.nocolor:
        for x in kwds: 
          self.report = self.report.replace(x[0], x[1] + x[0] + endcode)
      print(self.report)
    elif self.args.form == 'html':
      parsedfile = open(join(self.args.projpath, splitext(self.filename)[0] + ".html"), 'w')
      self.report = self.report.replace('\n', '<br/>')
      parsedfile.write(f"<html>{self.report}</html>")
  #


if __name__ == '__main__':
  tp = UnityTestParser()
  tp.RunTests()
  tp.ParseResults()
