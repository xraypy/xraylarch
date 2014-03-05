\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{puthesis}
         [2008/05/02 v1.4 Princeton University Thesis class]
\RequirePackage{setspace}
\RequirePackage{ccicons}
\RequirePackage{ifthen}
\newcounter{subyear}
\setcounter{subyear}{\number\year}
\def\submitted#1{\gdef\@submitted{#1}}
\def\@submittedyear{\ifnum\month>10 \stepcounter{subyear}\thesubyear
  \else\thesubyear\fi}
\def\@submittedmonth{\ifnum\month>10 January\else\ifnum\month>5 November
  \else June\fi\fi}
\def\copyrightyear#1{\gdef\@copyrightyear{#1}}
\def\@copyrightyear{\number\year}
\def\adviser#1{\gdef\@adviser{#1}}
\long\def\@abstract{\@latex@error{No \noexpand\abstract given}\@ehc}
\newcommand*{\frontmatter}{
  \pagenumbering{roman}
  }
\newcommand*{\mainmatter}{\pagenumbering{arabic}}
\newcommand*{\makelot}{}
\newcommand*{\makelof}{}
\newcommand*{\makelos}{}
\newcommand*{\maketoc}{
  % Add ToC to the pdfbookmarks as a section, but not to the ToC itself.
  % only if we have the hyperref command that is necessary
  \ifdefined\pdfbookmark
     \phantomsection
     \pdfbookmark[1]{\contentsname}{Contents}
  \else
  \fi

  \tableofcontents
  \clearpage
}
%% Setup a command to add extra space only if in singlespacing mode
\newcommand*{\extravspace}[1]{\vspace{0in}}
%% Setup a command to set spacing for body text; also used to restore spacing after long tables in document
\newcommand*{\bodyspacing}{
  \doublespacing
}
%% boolean for twosided/onesided
\newboolean{@myopt@oneside}
\setboolean{@myopt@oneside}{true}
%% Setup a command to set spacing for long tables, to be used manually in document
\newcommand*{\tablespacing}{
  \singlespacing
}
%% Command inserted into the document immediately after \begin{document} to place all frontmatter
%%   This was formerly named 'begincmd' and called below in \AtBeginDocument{}
%%   However, that is not compatible with package 'hyperref'. \tableofcontents needs
%%   to be declared from within the document itself. 
\newcommand*{\makefrontmatter}{
\bodyspacing
\frontmatter\maketitlepage\makecopyrightpage\makeabstract
\makeacknowledgements\makededication\maketoc
\makelot\clearpage\makelof\clearpage\makelos
\clearpage\mainmatter
}
\def\@submitted{\@submittedmonth~\@submittedyear}
\def\@dept{Mathematics}
\def\@deptpref{Department of}
\def\departmentprefix#1{\gdef\@deptpref{#1}}
\def\department#1{\gdef\@dept{#1}}
\long\def\acknowledgements#1{\gdef\@acknowledgements{#1}}
\def\dedication#1{\gdef\@dedication{#1}}
\newcommand{\maketitlepage}{{
  \thispagestyle{empty}
  \sc
  \vspace*{0in}
  \begin{center}
    \LARGE \@title
  \end{center}
  \vspace{.6in}
  \extravspace{.6in}
  \begin{center}
    \@author
  \end{center}
  \vspace{.6in}
  \extravspace{.6in}
  \begin{center}
    A Dissertation \\
    Presented to the Faculty \\
    of Princeton University \\
    in Candidacy for the Degree \\
    of Doctor of Philosophy
  \end{center}
  \vspace{.3in}
  \extravspace{.3in}
  \begin{center}
    Recommended for Acceptance \\
    by the \@deptpref \\
    \@dept \\
    Adviser: \@adviser
  \end{center}
  \vspace{.3in}
  \extravspace{.3in}
  \begin{center}
    \@submitted
  \end{center}
  \clearpage
  }}
\newcommand*{\makecopyrightpage}{
  \thispagestyle{empty}
  \vspace*{0in}
  \begin{center}
    \copyright\ Copyright by \@author, \@copyrightyear. All rights reserved. \\
    \vspace{1in}
    \begin{minipage}[c]{0.2\linewidth}
      \hfill {\Huge \ccLogo~\ccAttribution}
    \end{minipage}
    \hspace{0.1cm}
    \begin{minipage}[c]{0.7\linewidth}
      This work is licensed under a Creative Commons Attribution-3.0 United States License. \\
      \url{http://creativecommons.org/licenses/by/3.0/us/}
    \end{minipage}
  \end{center}
  \clearpage}
\newcommand*{\makeabstract}{
  \newpage
  \addcontentsline{toc}{section}{Abstract}
  \begin{center}
  \Large \textbf{Abstract}
  \end{center}
  \@abstract
  \clearpage
  }
\def\makeacknowledgements{
  \ifx\@acknowledgements\undefined
  \else
    \ifdefined\phantomsection
     % makes hyperref recognize this section properly for pdf links
     \phantomsection
    \else
    \fi

    \addcontentsline{toc}{section}{Acknowledgements}
    \begin{center}
      \Large \textbf{Acknowledgements}
    \end{center}
    \@acknowledgements
    \clearpage
  \fi
  }
\def\makededication{
  \ifx\@dedication\undefined
  \else
    \vspace*{1.5in}
    \begin{flushright}
      \@dedication
    \end{flushright}
    \clearpage
  \fi
  }
\DeclareOption{lot}{\renewcommand*{\makelot}{
  \ifdefined\phantomsection
    % makes hyperref recognize this section properly for pdf links
    \phantomsection
  \else
  \fi
  \addcontentsline{toc}{section}{List of Tables}\listoftables}}
\DeclareOption{lof}{\renewcommand*{\makelof}{
  \ifdefined\phantomsection
    % makes hyperref recognize this section properly for pdf links
    \phantomsection
  \else
  \fi
  \addcontentsline{toc}{section}{List of Figures}\listoffigures}}
\DeclareOption{los}{
  \renewcommand*{\makelos}{
    \RequirePackage{losymbol}
    \section*{List of Symbols\@mkboth {LIST OF SYMBOLS}{LIST OF SYMBOLS}}
    \@starttoc{los}
  \ifdefined\phantomsection
    % makes hyperref recognize this section properly for pdf links
    \phantomsection
  \else
  \fi
    \addcontentsline{toc}{section}{List of Symbols}
  }
}
\DeclareOption{singlespace}{
  \renewcommand*{\bodyspacing}{
  \singlespacing
  }
  %% Add extra space only if in singlespacing mode
  \renewcommand*{\extravspace}[1]{\vspace{#1}}
}
%% Doublespacing is the default for the thesis -- need not be declared.
\DeclareOption{doublespacing}{
  \renewcommand*{\bodyspacing}{
  \doublespacing
  }
}
%% oneside/twoside options
\DeclareOption{oneside}{\setboolean{@myopt@oneside}{true}}
\DeclareOption{twoside}{\setboolean{@myopt@oneside}{false}}

\DeclareOption*{\PassOptionsToClass{\CurrentOption}{report}}
\ProcessOptions

\ifthenelse{\boolean{@myopt@oneside}}
    {\PassOptionsToClass{oneside}{report}}
    {\PassOptionsToClass{twoside}{report}}

%% Not necessary to specify the point size - we inherit it from above
%% \LoadClass[12pt]{report}
\LoadClass{report}
\ifthenelse{\boolean{@myopt@oneside}}
    {
\setlength{\oddsidemargin}{.5in}   %{.4375in}
\setlength{\evensidemargin}{.5in} %{.4375in}
}{
\setlength{\oddsidemargin}{.5in}   %{.4375in}
\setlength{\evensidemargin}{0in} %{.4375in}
}
\setlength{\topmargin}{-.5in}  %{-.5625in}
\setlength{\footskip}{.25in} % to put page number 3/4" from the bottom of the page (1/4" from bottom of body text)
\setlength{\textheight}{9in}
\setlength{\textwidth}{6in}

%%% Alter LaTeX defaults to try to eliminate all widows and orphans
\clubpenalty=10000
\widowpenalty=10000

%%% try to avoid overfull lines by limiting how far it is okay to exceed the margins
%%% http://www.tex.ac.uk/cgi-bin/texfaq2html?label=overfull
\setlength{\emergencystretch}{2em}

\long\def\abstract#1{\gdef\@abstract{#1}}
%% 'begincmd' no longer used -- insert \makefrontmatter in the document instead. See above. 
%\AtBeginDocument{\begincmd}
\endinput
%% 
%% End of file `puthesis.cls'.
