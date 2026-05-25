%% bachelorthesis.cls
%% SDU TEK Bachelor's Project Report class
\NeedsTeXFormat{LaTeX2e}
% ---------------------------------------------------------------------------
% Capture the cls's own path BEFORE *anything* else
% ---------------------------------------------------------------------------
\edef\bt@clsfullpath@raw{\@filef@und}
\RequirePackage{xstring}
\StrSubstitute{\bt@clsfullpath@raw}{"}{}[\bt@clsfullpath]
\filename@parse{\bt@clsfullpath}
\xdef\bt@templatedir{\filename@area}
\ifx\bt@templatedir\@empty
  \def\bt@templatedir{./}%
\fi
\typeout{[bachelorthesis] cls raw : <\bt@clsfullpath@raw>}
\typeout{[bachelorthesis] cls path: <\bt@clsfullpath>}
\typeout{[bachelorthesis] tpl dir : <\bt@templatedir>}
% ---------------------------------------------------------------------------
% Provide the class. The kernel insists on comparing the literal argument
% of \ProvidesClass against \@currname, which differs whenever the class
% is loaded via a path (e.g. `\documentclass{../SDU_Template/bachelorthesis}').
% That mismatch produces the cosmetic
%   "You have requested document class `<path>', but the document class
%    provides `bachelorthesis'."
% warning. The version metadata it sets internally (`ver@<currname>.cls')
% is built off \@currname and is therefore correct already, so we just
% silence the kernel warning for the call.
% ---------------------------------------------------------------------------
\begingroup
  \let\@latex@warning\@gobble
  \let\@latex@warning@no@line\@gobble
  \ProvidesClass{bachelorthesis}%
    [2026/05/04 v1.17 SDU TEK Bachelor's Project Report]
\endgroup
% ---------------------------------------------------------------------------
% Base class
% ---------------------------------------------------------------------------
\DeclareOption*{\PassOptionsToClass{\CurrentOption}{article}}
\ProcessOptions\relax
\LoadClass[a4paper,11pt]{article}
% ---------------------------------------------------------------------------
% Packages
% ---------------------------------------------------------------------------
\RequirePackage[utf8]{inputenc}
\RequirePackage[T1]{fontenc}
\RequirePackage[english]{babel}
\RequirePackage[margin=2.5cm]{geometry}
\RequirePackage{lmodern}
\RequirePackage{amsmath,amssymb,amsfonts}
\RequirePackage{algorithmic}
\RequirePackage{graphicx}
\RequirePackage[x11names,svgnames]{xcolor}
\RequirePackage{pifont}
\RequirePackage{textcomp}
\RequirePackage{plantuml}
\@ifundefined{setpythontexlistingenv}{}{\setpythontexlistingenv{pylisting}}
\RequirePackage[acronym,automake,nogroupskip]{glossaries}
\RequirePackage{subfiles}
\RequirePackage{tabularx}
\RequirePackage{booktabs}
\RequirePackage{array}
\RequirePackage{longtable}
\RequirePackage{cuted}
\RequirePackage{caption}
\RequirePackage{placeins}
\RequirePackage{float}
\RequirePackage{setspace}
\RequirePackage{ragged2e}
\RequirePackage{minted}
\RequirePackage{csquotes}
\RequirePackage[colorlinks=true,linkcolor=black,citecolor=black,hyperfootnotes=true]{hyperref}
\RequirePackage[capitalise]{cleveref}
\RequirePackage{biblatex}
\RequirePackage{microtype}
\RequirePackage{xltabular}
% ---------------------------------------------------------------------------
% Page style
% ---------------------------------------------------------------------------
\pagestyle{plain}
% ---------------------------------------------------------------------------
% Image search path
% ---------------------------------------------------------------------------
\graphicspath{%
  {\bt@templatedir}%
  {\bt@templatedir assets/}%
  {./assets/}%
  {./}%
  {../assets/}%
  {../}%
  {../../assets/}%
  {../../}%
}
% ---------------------------------------------------------------------------
% BibTeX logo
% ---------------------------------------------------------------------------
\def\BibTeX{{\rm B\kern-.05em{\sc i\kern-.025em b}\kern-.08em
    T\kern-.1667em\lower.7ex\hbox{E}\kern-.125emX}}
% ---------------------------------------------------------------------------
% IEEE-style author block compatibility
% ---------------------------------------------------------------------------
\providecommand{\IEEEauthorblockN}[1]{{\normalsize #1}\\[2pt]}
\providecommand{\IEEEauthorblockA}[1]{%
  \begin{tabular}[t]{@{}>{\small}c@{}}#1\end{tabular}%
}
% ---------------------------------------------------------------------------
% Title page
% ---------------------------------------------------------------------------
\renewcommand{\maketitle}{%
  \pagenumbering{roman}%
  \begin{titlepage}%
    \let\footnote\thanks
    \centering
    \let\@TitleOrigCr\\
    \renewcommand\\{\@TitleCrCheck}%
    \def\@TitleCrCheck{\@ifnextchar[\@TitleCrWithArg\@TitleCrNoArg}%
    \def\@TitleCrWithArg[##1]{\ifvmode\else\@TitleOrigCr[##1]\fi}%
    \def\@TitleCrNoArg{\ifvmode\else\@TitleOrigCr\fi}%
    \null\vskip 8em
    {\LARGE\@title\par}
    \vskip 3em
    {\large
      \lineskip .75em
      \begin{tabular}[t]{c}%
        \@author
      \end{tabular}\par
    }
    \vskip 1.5em
    {\large \@date\par}
    \vfill
    \includegraphics[width=0.35\textwidth]{sdu_logo}\@TitleOrigCr[1em]
    {\large The Maersk Mc-Kinney Moeller Institute}
    \vspace*{1em}
  \end{titlepage}%
  \setcounter{footnote}{0}%
}
% ---------------------------------------------------------------------------
% Abstract environment (its own page)
% ---------------------------------------------------------------------------
\renewenvironment{abstract}{%
  \clearpage
  \thispagestyle{plain}%
  \begin{center}
    {\Large\bfseries\abstractname\par}
  \end{center}
  \vspace{1em}
  \par\noindent\ignorespaces
}{%
  \par\clearpage
}
% ---------------------------------------------------------------------------
% \tableofcontents and \listoffigures on their own pages.
% \listoffigures additionally prints the list of tables underneath.
% ---------------------------------------------------------------------------
\let\bt@orig@toc\tableofcontents
\renewcommand{\tableofcontents}{%
  \clearpage
  \thispagestyle{plain}%
  \bt@orig@toc
  \clearpage
}
\let\bt@orig@lof\listoffigures
\let\bt@orig@lot\listoftables
\renewcommand{\listoffigures}{%
  \clearpage
  \thispagestyle{plain}%
  \bt@orig@lof
  \par\vspace{1.5em}
  \bt@orig@lot
  \clearpage
}
\renewcommand{\listoftables}{}
% ---------------------------------------------------------------------------
% Front-matter / main-matter switching
% ---------------------------------------------------------------------------
\newif\if@bt@mainstarted
\@bt@mainstartedfalse
\newcommand{\mainmatter}{%
  \clearpage
  \pagenumbering{arabic}%
  \setcounter{page}{1}%
  \@bt@mainstartedtrue
}
\let\bt@orig@section\section
\renewcommand{\section}{%
  \@ifstar{\bt@orig@section*}{\bt@section@regular}%
}
\newcommand{\bt@section@regular}{%
  \if@bt@mainstarted\else\mainmatter\fi
  \bt@orig@section
}
\endinput
