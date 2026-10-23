# Audax Data Manager 1.6 Release

## Release Date: Oct 27 2026

## Release Notes

  - New features:
    - added support for composite primary keys in ERD module #914 

  - Bugs fixed:
    - fixed data editor row updates when table contains composite primary keys #912
    - fixed query result data export on desktop builds #916
    - fixed scrollable area in web file manager "list" view #872


# Audax Data Manager 1.6 Release

## Release Date: Sep 01 2026

## Release Notes

  - Upgrade Notes:
    - rebranded the application as "Audax Data Manager": new logos, icons, splash screen and installer graphics throughout the app #886
    - the application data directory has been renamed from ~/.pgmanage to ~/.audaxdm (on Windows: %USERPROFILE%\.pgmanage to %USERPROFILE%\.audaxdm); existing data is migrated automatically on first launch #889
    - the database and log files have been renamed from pgmanage.db/pgmanage.log to audaxdm.db/audaxdm.log as part of the same automatic migration #889
    - the Windows uninstaller no longer removes application data by default

  - New features:
    - rewrote the Entity Relationship Diagram: intelligent relationship-edge routing, added snap-to-grid positioning, improved node/edge selection, add cardinality markers, viewport save/restore and a dedicated full-screen controls panel #885
    - rewrote the Database Console: make it behave like a real console, added command history navigation with the Up/Down keys and active database switching via the "\c" meta-command for Postgres #894
    - implemented visual feedback and keyboard navigation for moving focus between application panels #842
    - added support for SQLite3 database file paths containing a tilde (~)
    - implemented "rows affected" display on Query tab toolbar #701

  - UI/UX Improvements:
    - Database object icons and context menu icons/paddings now scale with the app font size setting #908
    - limited the minimum size of the application container and added scrollbars when the window is smaller than it, preventing UI breakage #726
    - the onboarding widget is now only shown on the Welcome screen #784
    - improved text truncation of recent connections subtitles to keep the most important part visible #804
    - improved Settings > Hotkeys tab layout: more rows fit on screen and columns are wide enough for larger key combinations like Ctrl+Shift+Space
    - implemented live resize of the built-in SSH terminal when font size or window size changes #897
    - improved desktop app startup time by switching the Linux build to PyInstaller's one-directory mode, avoiding double compression with AppImage #879

  - Bugs fixed:
    - fixed a remote code execution (RCE) vulnerability via psql meta-commands during plain-format server restore #899
    - fixed an XSS vulnerability in backup/restore preview alert messages #902
    - fixed database passwords being retained in the backup/restore process environment
    - fixed backup argument handling: missing --dbname option, invalid backup type validation, and pigz pipeline formatting in command previews
    - fixed pigz backup failing when file paths contain spaces #909
    - fixed ERD tab failing to generate relationship edges for foreign keys referencing quoted/uppercase table names #882
    - fixed DDL content being lost when toggling the Properties panel #907
    - fixed layout breakage when tabbing through DDL/Properties panel elements #906
    - closing a connection now also closes its open tabs #911
    - fixed Data Editor footer bar jumping when the tab regains focus
    - fixed light terminal theme rendering the cursor's character invisible

  - Other Changes
    - updated the docs link and wording of the onboarding wizard link on the Welcome screen #898
    - updated pev2 to 1.22
    - bumped nwjs from 0.77.0 to 0.114.0 to fix CSS rendering issues in ERD tab on Windows and macOS
    - bump cryptography from 45.0.5 to 46.0.7
    - bump django from 5.2.12 to 5.2.15
    - bump psycopg2 from 2.9.11 to 2.9.12
    - bump RestrictedPython from 8.0 to 8.3
    - bump oracledb from 3.4.2 to 4.0.1
    - bump pymysql from 1.1.2 to 1.1.3
    - bump django-vite from 3.0.4 to 3.0.6
    - bump prettytable from 3.16.0 to 3.17.0
    - bump ace-builds from 1.39.1 to 1.43.6
    - bump axios from 1.16.0 to 1.17.0
    - bump bootstrap from 5.3.3 to 5.3.8
    - bump fuse.js from 7.1.0 to 7.3.0
    - bump knex from 3.1.0 to 3.2.10
    - bump lodash from 4.17.21 to 4.18.1
    - bump pinia from 2.2.2 to 2.3.1
    - bump sql-formatter from 15.4.1 to 15.7.4
    - bump vue from 3.5.13 to 3.5.32
    - excluded django.contrib.admin and non-English locale/timezone data files from the PyInstaller bundle to reduce binary size #498

# Audax Data Manager 1.5 Release

## Release Date: Jun 16 2026

## Release Notes

  - New features:
    - implemented support for keyboard navigation in Database Explorer using Page-Up, Page-Down, Home, End and arrow keys #747
    - implemented support for opening context menu with keyboard "Context Menu" key in Data Editor and Query Tabs #745
    - implemented support for copying/pasting cell regions in the Data Editor #782
    - implemented hotkey support for Copy/Paste and Clear actions in data grids #749
    - implemented full-screen mode support for Data Editor and ERD tabs #791
    - implemented quick access to theme and font size settings in the app sidebar #787
    - implemented the "unsaved data" warning when user tries to close a workspace or tab #779
    - implemented command history deduplication to hide identical subsequent commands from history #780
    - implemented support for editing cell data in a dedicated modal window in addition to inline editing #781
    - implemented proper handling of Postgres byte array data in Query and Data Editor tabs #821
    - implemented clipboard Copy/Paste context menu options in Database Console and SSH Terminal tabs #820
    - implemented Oracle support in Schema Editor #840
    - implemented support for renaming database indexes in MySQL, MariaDB, SQLite3 and MS SQL Server #823
    - implemented support for updating column comments for Postgres, MySQL and MariaDB in schema editor 
    - implemented support for multiple versions of Postgres binaries #827

  - UI/UX Improvements:
    - all modal windows can now be closed by Escape key #750
    - it is now possible to quickly select a query history record and load it in Query Editor by double clicking on it, thanks @ccurvey #750
    - added "mac-style" text truncation in workspace tabs #288
    - extended clickable area of Database Explorer rows #776
    - extended clickable area of Data and Schema Editor grid action icons #800
    - extended clickable area of Quick Search icon and DDL tab Edit icon
    - clicking on the settings icon of the Welcome Screen shortcuts area now opens the Shortcuts tab in the Settings modal #801
    - adaptive layout is now used for data grids when entering fullscreen mode in Query tab #793
    - full-screen toggle controls now display a different icon based on the current state #792
    - prevent slight tab width shifts between active and inactive tab states #789
    - use more subtle colors for Database Explorer tree view toggle controls #788
    - increased default UI font size from 12px to 16px to match modern display pixel density #817
    - adjusted database tabs UI to scroll the newly opened tab into view #662
    - move database query error messages the Messages tab; automatically activate Messages tab it if error occurs. Thanks @ccurvey for reporting the issue #700
    - improved Database Explorer responsiveness and loading speed when working with thousands of tables #837
    - improved DB explorer expanded node positioning to fully remain in the view port after node is auto-scrolled #847
    - improved DB explorer expanded node positioning to fully remain in the view port after Quick Search/Jump-to #846
    - clicking on minimized DDL / Properties component will expand it #849
    - added helpful tooltips to Settings, Backup and Restore tabs #824
    - reorganized context menus in Snippets module to be consistent with the rest of the app #809
    - unify data grid context menu styles to be consistent with the rest of the app #807
    - improved Database Explorer layout scaling when font size change #868

  - Bugs fixed:
    - fixed color markers not showing in the Data Editor after clipboard copy was used on that row #765
    - fixed hotkey conflicts by disallowing the registration of certain standard key combinations #748
    - fixed right-click on the Databases node in MySQL/MariaDB changing the selected database #806
    - fixed Data Editor cell data being fully cleared when cell is being edited and Backspace key is used
    - fixed Oracle DB Tree APIs when working with quoted tables #839
    - fixed SQL templates not working with quoted tables #859
    - fixed ERD tab not showing columns of tables with quoted name #858
    - fixed Query data context menu item doesn't work with quoted tables #860
    - fixed Data Editor not working with quoted tables #861
    - fixed Data Editor not recognizing record changes when editing data in quoted tables (postgresql) #866
    - made pigz and postgres native backup compression options mutually exclusive to prevent double compression of DB backups #832
    - fixed deadlocks in QueryTablesFields when working with SQLite3 databases #837
    - fixed Schema editor -> Foreign keys -> Column dropdown not showing all values #845
    - fixed DDL / Properties content not refreshed after search/jump-to #848
    - fixed snippet editor tab remaining open when the snippet is deleted #851
    - fixed incorrect database schema order in Database Explorer #843
    - fixed incorrect database partition order in Database Explorer #853
    - fixed Database Explorer API request failing when working with quoted tables in Oracle #839

  - Other Changes
    - exposed cherrypy socket queue and thread pool size as config parameters of pgmanage-server
    - implemented various enhancements in the web file manager dialog to handle huge files #826
    - extended logging_filter rules to strip DB credentials from log lines containing DB connection strings
    - optimized database metadata loading to make fewer trips to the database #837
    - bump django from 4.2.23 to 5.2.12
    - bump pymysql from 1.1.1 to 1.1.2
    - bump psutil from 6.1.1 to 7.2.2
    - bump oracledb from 3.2 to 3.4.2
    - bump sqlparse from 0.5.3 to 0.5.5
    - bump pymssql from 2.3.7 to 2.3.10
    - bump Node.js version from 18x to 22x
    - bump vite from 5.4.10 to 6.3.5
    - bump vitest from 2.1.9 to 3.2.4
    - bump @vitest/ui from 2.1.9 to 3.2.4
    - bump @vitest/coverage-v8 from 2.1.9 to 3.2.4
    - bump vite-plugin-node-polyfills from 0.22.0 to 0.25.0
    - bump @vitejs/plugin-vue from 5.1.5 to 5.2.4
    - bump happy-dom from 15.11.7 to 20.6.2

# PgManage 1.4.1 Bugfix Release

## Release Date: Jan 20 2026

## Release Notes

  - Bugs fixed:
    - fixed unwanted change of last used database when Databases tree node is clicked in DB Explorer #806
    - fixed Postgres DB connection close when Cancel Query is clicked in Query tab #802
    - fixed incorrect tab displayed in Settings modal when clicking Shortcuts icon on the Welcome screen #801
    - fixed selected database not always changing when using Quick Search #814
    
  - Other Changes
    - migrate to appimagetool 1.9.1 for Linux builds
    - update copyright years in Windows installer


# PgManage 1.4 Release

## Release Date: Nov 18 2025

## Release Notes

  - New features:
    - implemented support for MS SQL Server databases 
    - implemented keyboard navigation in Data Editor grid #736
    - implemented support for partial/range selection in data grids for selective copying and other operations #752
    - implemented a dedicated DB object drop/deletion dialog to replace template based workflow #734
    - implemented "quick search/jump to" feature in DB object tree for quicker navigation #667
    - implemented "pin database" feature for quicker navigation #237
    - implemented postgres server log viewer #658
    - implemented pan, zoom and layout save/restore in ERD tab, added a dedicated toolbar for pan/zoom #659
    - implemented support for mDNS resolving when connecting to database server #673
    - implemented redraw of customized dashboard widgets when widget settings change #626
    - implemented display of table index details in DDL tab for MariaDB and MySQL #704
    - implemented foreign key support in schema editor #251
  
  - Bugs fixed:
    - relaxed custom widget validation rules to allow blank chart generation code #720
    - fixed an error in Data Editor when saving multiple rows in Oracle #737
    - fixed an error when running multiple SQL statements against Oracle database #738
    - fixed error when opening Oracle database connections in desktop app builds #767
    - fixed command history modal not displaying the most recent query #740
    - fixed the issue where pgmanage tabs could become unresponsive if the network connection stalls
    - don't show Explain/Explain Selection features when working with non-postgres databases
    - properly handle null passwords when bulding DB connection string
    - fixed race condition resulting in intermittent Schema Editor errors after modifying table in MySQL or MariaDB #755
    - fixed incorrect default_value in get_table_definition* API endpoints #754
    - fixed a bug in Schema Editor where "touched" column default values cannot be reverted to their initial state #757
    - fixed missing color markers on altered table rows in Data Editor if Clipboard Copy command was used on them before #765

  - UI/UX Improvements:
    - reorganized DB tree context menus #668
    - improved postgres notice display in Query Tab: added color labels and refined notice formatting #725
    - improved nested context menu navigation when moving cursor from parent to child menu
    - improved stylesheets for snippets panel tab
    - right-justify integers and numerics in query results data grid #681
    - improved formatting of DB error toasts and dialogs #739
    - tweaked app scrollbar sizes to make them easier to grab
    - removed unnecessary confirmation when closing DB workspaces, ask for confirmation only if there's unsaved data
    - improved formatting and readability of Oracle DB sessions tab
    - enlarged clickable area of DB tree node expand/collapse icon to make it easier to click
    - added SQL formatting for DDL tab content when working SQLite3 databases
    - don't immediately show the loader overlay in DDL/Properties tab when changing selected DB object

  - Other Changes
    - updated python from 3.9.13 to 3.11.13
    - updated cherrypy from 18.1.1 to 18.10.0
    - updated psycopg2 from 2.9.10 to 2.9.11
    - extracted app SQL templates into separate modules
    - removed redundant curly braces from postgres SQL templates
    - use user id instead of user username for process log file names
    - removed unnecessary blank lines between process log records
    - use native prettytable features when generating psql console command list

# PgManage 1.3.1 Bugfix Release

## Release Date: Aug 5 2025

## Release Notes

  - Bugs fixed:
    - fixed error when loading foregin key information in DB Tree in SQLite3 #682
    - fixed error when loading index information in DB Tree in Mariadb #688
    - fixed incorrect stylesheets for password strength validation widget
    - fixed erroneous "Discard Changes" warning when switching between conections in connection manager #698
    - fixed issue with incorrect where clause generated when using Data Editor query filter in Oracle
    - fixed erros when loading DDL for metadata link objects in DB tree
    - fixed back-end issue with idle Schema Editor thread not always getting terminated
    - fixed "autocommit" checkbox not working for Oracle DB connections
    - fixed validation errors when entering octal file permissions in Server Configuration Tab #705
    - fixed error when rolling back Postgres Server Configuration snapshots that have values not applicable to the current server setup
    - fixed errors when restoreing Postgres Server Configuration for databases running with non-english locales #707
    - fixed query result file export when query result have duplicate column names #715
    - fixed query result copy as JSON when query result have duplicate column names #712
    - fixed isssue with saving custom monitoring widgets without chart code block defined #720
    
  - Other Changes
    - updated restrictedpython from 7.4 to 8.0
    - updated django from 4.2.19 to 4.2.23 
    - updated oracledb from 2.5.1 to 3.2.0
    - updated cryptography from 41.0.7 to 45.0.5
    - updated nw.js from 0.69.1 to 0.77.0
    - refactored database capability flags code in back-end
    - removed unnecessary files from binary packages
    - minor layout fixes and improvements

# PgManage 1.3 Release

## Release Date: June 17 2025

## Release Notes

  - New features:
    - new visual data filtering UI in data editor #483
    - new monitoring widget management UI with support for reordering of dashboard widgets #617
    - new widget component layout with cleaner and easier to read UI #618
    - new implementation of dashboard widget graphs with improved readability and better handling of large amounts of datapoints #605
    - extend Mysql monitoring widgets to support Mariadb
    - added support for exporting query results in JSON format
    - added support for code folding in SQL editor
    - set backup type based on output file extension, set extension base on output type #531
    - added Postgres documentation links to SQL templates for quicker docs access
    - added column alias support in autocomplete engine
    - added advanced clipboard copy for data grids #217
    - added support for running EXPLAIN on a selected part of the query #533
    - added "copy to editor" feature for DDL tab and "Generated SQL" preview box components #536
    - new cell data viewer modal with syntax highlighting and support different data types
    - added support for Postgres 17
    
  - Bugs fixed:
    - removed unnecessary entries from info.plist on Mac builds which associated Pgmanage with some file extensions #620
    - added logic for handing mutually-exclusive --create and --single-transaction options in Database Restore tab
    - fixed incorrect colors for disabled inputs in dark theme
    - don't allow multiple monitoring dashboard within the same DB workspace
    - fixed Postgresql Alter View template
    - fixed autocomplete switch colors in dark theme
    - fixed DB object tree node data not loading in some cases
    - prevent starting duplicate backup/restore jobs #572
    - fixed empty SSL option appearing in connection form when connection type is changed #674
    
  - UI/UX Improvements:
    - improved console tab size change handling
    - improved readability of Backends tab UI
    - added data loading/saving indication for data editor tab
    - added support for keyboard navigation for searchable drop-down lists
    - improved layout of Server Configuration tab toolbar
    - show query result messages for all supported databases
    - improved date-range picker in command history modals
    - improved command history modal layout
    - add support for live update of widget font size and colors when theme or font size is changed in app settings
    - improved data editor grid rendering performance when working with large number of rows
    - joined Run and Run selection buttons into a single block, moved autocommit option in its drop-down menu #507
    - backup/restore jobs are now ordered by job start time, from newest to oldest
    - the View Content data grid context menu is now disabled when multiple cells are selected
    - long backup/restore file paths are now truncated in the middle to improve readability
    - added "Discard Changes" warning when closing Data Editor
    - improved data grid cell rendering performance for cells containing large amounts of data

  - Other Changes
    - cleaned up legacy/unused sass styles
    - Django updated from 4.2.17 to 4.2.19
    - openpyxl updated from 3.0.10 to 3.1.3
    - restrictedpython updated from 6.0 to 7.4
    - psutil updated from 5.9.8 to 6.1.1
    - oracledb updated from 2.2.1 to 2.5.1
    - sqlparse update from 0.5.1 to 0.5.3
    - improved front-end error logging
    - ace-editor updated from 1.36.2 to 1.39.1
    - axios updated from 1.7.7 to 1.8.4
    - pev2 update from 1.12.1 to 1.14.0
    - splitpanes updated from 3.1.5 to 3.2
    - vue updated from 3.5.4 to 3.5.13
    - cleaned up back-end code
    - randomize start time of monitoring dashboard widgets data polling to reduce DB usage spikes
    - execute schema editor requests via long polliing
    - don't add information_schema and pg_catalog data to autocomplete engine

# PgManage 1.2.1 Bugfix Release

## Release Date: Feb 13 2024

## Release Notes
    
  - Bugs fixed:
    - fixed error notification link colors, added minor layout tweaks
    - fixed DB object tree node data refresh in some edge-cases
    - fixed erroneous "Discard Changes" warning when closing Query tab
    - fixed connectivity issues in built-in SSH terminal
    - fixed bug with multiple tabs highlighted as "active" #570
    - fixed app crash when schema editor is opened immediately after DB workspace is loaded
    - fixed bug with DROP database unable to complete in some cases #582
    - fixed bug with DB object tree context menu disappearing when monitoring dashboard refreshes #607
    - fixed race condition in Backup/Restore job status modal when running multiple jobs simultaneusly
    - fixed bug that allowed to register duplicate hotkey actions #611
    - fixed bug that caused old SQLite3 DB file being used when connection properties updated with a new file #598
    - fixed SQLite3 tables not ordered by name in DB object tree #596
    
  - Other Changes:
    - bumped happy-dom version to fix potential security vulnerability in dev environment
    - silenced SASS deprecation warnings during js bundle build
    - plus icons are now used for all context menus associated with "create" action #557
    - improved readability of multiple modal windows shown on-top of each other
    - improved SQLite3 DB connection "Test"
    - improved database metadata loading and autocomplete engine initialization


# PgManage 1.2 Release

## Release Date: Nov 07 2024

## Release Notes

  - New features:
    - implemented support for adding/changing table indexes in Schema Editor
    - implemented Postgres role editor
    - added SQL error annotations in query editor
    - significant code completion improvements: added context-aware schema, table, view, column and function completions
    - added support for Postgres byte array display query results data grid
    
  - Bugs fixed:
    - fixes a bug in connection manager where "Discard changes" confirmation was shown after clicking "Test Connection" button
    - fixed a bug when PgManage was trying to restore tabs for closed DB workspaces
    - fixed a bug when "Discard changes" confirmation appeared after running "Explain/Analyze" and then closing DB workspace
    - fall back to unencrypted ssh key when no password is provided (thanks @El-Virus)
    - use user-provided database password instead of previously stored one when "Test connection" is clicked in connection manager
    - fixed a bug when backup/restore background job info was potentially accessible by other pgmanage user accounts
    - fixed a bug when redundant database back-end was instantiated when requesting database auto-completion metadata 
    - fixed a rare race condition when opening new database workspace
    - rearranged parts of DROP INDEX query template to make it runnable without needing extra modifications by the user
    - fixed a bug in Monitoring Dashboard when "Refresh all widgets" button was doing nothing after deleting all and restoring some monitoring widgets
    - fixes a bug in connection manager where "Discard changes" confirmation was shown for connections with passwords auto-filled by the browser
    - fixes a bug in schema editor where "DEFAULT" part of column definition was rendered regardless of presence of column default value
    
  - UI/UX Improvements:
    - new application startup screen
    - improved naming for exported CSV/XLS files
    
  - Other Changes
    - Django updated from 4.2.11 to 4.2.16
    - cryptography updated from 36.0.2 to 41.0.7
    - pymysql updated from 1.0.x to 1.1.1
    - psycopg2 updated from 2.9.5 to 2.9.9
    - oracledb updated form 1.3.1 to 2.2.1
    - other occurrences of highlighed selection in query editor are now case-insensitive
    - implemented custom SESSION_SERIALIZER for improved sesion handling security
    - eager-load QueryTab components when opening database workspace for improved app responsiveness
    - added uniqueness validation to connection group names
    - removed unnecessary files from windows build of PgManage
    - changed default value for CSV separator setting
    - improved database back-end cleanup when no keep-alive requests come from the front-end
    - don't show error toast when running Explain/Analyze if PEV2 can display these errors by itself

# PgManage 1.1.1 Release

## Release Date: Sep 04 2024

## Release Notes

  - New features:
    - added IPv6 support for database connections
    - allow using UNIX domain socket paths in connection form -> server field #438
    - allow empty server values in the connection form for Postgres connections
    - password prompt will now be shown when user tries to establish database connection with wrong password
    - queries in console query history modal can now be copied to query tab with a double-click
    - console history buffer is now cleared from memory when "clear console" button is clicked

  - Bugs fixed:
    - fixed unrestricted code execution vulnerability in monitoring widget back-end. The issue was reported by Andrew Effenhauser, Ayman Hammad and Daniel Crowley of X-Force Red
    - fixed Entity Relationship not rendering diagram for some database layouts
    - fixes issue when expanded DB object tree node was not always scrolled to the top of viewport
    - fixed missing GRANT statements when roles is displayed in DDL tab
    - fixed a bug when application tabs may become unresponsive some cases
    - various minor layout fixes and tweaks


# PgManage 1.1 Release

## Release Date: Jul 16 2024

## Release Notes

 - New features:
   - pgmanage now uses database-specific syntax highlighting rules in SQL editors depending on the database type
   - added support for displaying column data types in query results data grid
   - columns in query results data grid can now be minimized/maximized by double-clicking the column header
   - switchable data grid layouts in query tabs: adaptive, compact and fit-content can be selected by clicking the ellipsis icon on the top-left corner of the grid
   - existing DB connection can now be cloned in connection manager dialog
   - the size of the next loaded data chunk can now be selcted when using "fetch-more" feature for large query results
   - added multi-statement queries support for SQlite3
   - database connections can now have a color label to make it easier to differentiate between different environments
   - scram-sha256 password hashing is now used when changing Postgres role passwords

 - Major Bugs fixed:
   - fixed documentation urls in Postgres DB object tree context menus
   - disable connection test button when test is in progress
   - fixed 'fetch all records' feature when running queries on non-postgres databases
   - fixed reversed DB object tree node ordering for inherited tables, foreign tables, sequences views, materialized views, trigger functions, event triggers, procedures, aggregates, types, fdw and tablespaces
   - fixed incorrect count of table partitions displayed in DB object tree when tree is refreshed
   - fixed Postgres unique indexes not being displayed in DDL tab
   - fixed live theme switching issues for some modal dialogs
   - improved escaping of HTML characters in data grid cells to prevent potential XSS
   - fixes issue when query execution timer may not be stopped when user cancels the query
   - fixed data saving issues in table data editor when using a database other than the one specified in DB connection properties (databases other than Postgres were affected)
   - fixed data editor issues when user tried to apply multiple row changes at once on SQlite3
   - improved back-end query thread termination when long-running query is cancelled by the user
   - fixed long polling request clean-up when user closes application tabs
   - fixed memory leak when working with DB console or SSH terminals
   - fixed updating last used date for SSH connections
   - fixed intermittent pgmanage startup issues on Windows platform
   - fixed query results data export when query contains explain or explain analyze keywords

 - UI/UX Improvements:
   - 'fetch all records' is now also supported DB console tabs
   - removed unnecessary schema name prefixes from table partition names in DB object tree
   - added warning about unsaved changes in Postgres Seever configuration tab before close
   - added confirmation when deleting configuration change histore records in Postgres Server configuration tab
   - added support for showing newline characters in query results data grid cells
   - added support for showing null and blank values in query results data grid cells
   - data grid is no longer hidden for queries that return 0 rows
   - added visual hints for column resize handles in data grid headers
   - improved DB console and SSH terminal performance when displaying large amounts of text
   - significantly improved performance of query result data grids when working with large amounts of data
   - it is now possible to reuse a query from the history dialog by double clicking on the correspoding query cell

 - Other Changes
   - sshtunnel bumped from 0.1.5 to 0.4.0
   - optimized front-end imports to reduce js bundle size
   - optimized peformance of several back-end queries
   - project migrated from bootstrap 4 to bootstrap 5
   - pev2 bumped from 1.8 to 1.11
   - legacy code clean-up
   - removed support for EOL Postgres versions
   - added support for creating debug .appimage builds
   - added support for masking sensitive data in error logs
   - project migrated from django 3.2 to django 4.2
   - bumped xterm.js from 5.2 to 5.5


# PgManage 1.0.1 Bugfix Release

## Release Date: May 16 2024

## Release Notes

  - Bugs fixed:
   - trim explain/explain analyze prefix of the query when "explain" or "explain analyze" button is clicked
   - disable unnecessary row selection in command/query history data grid
   - fix cell data viewer modal working incorrectly when the cell contains numeric valueis Number
   - clean-up backup/restore job status polling when corresponding backup/restore tab is closed
   - make DB object tree resize line easier to grab when scrollbar is also present in DB object tree
   - fixed query results data-grid autosizing
   - fixed fetch more/fetch all records for SQLite3
   - disable drag-n-drop of DB session tabs above Connections/Welcome/Snippets sidebar items
   - don't hide connection/group form in connections dialog after connection/group is saved
   - add confirmation for connection group deletion
   - don't show the "unsaved changes" popup when user saved the new connection group and tries to select other group/connection


# PgManage 1.0 Release

## Release Date: Apr 17 2024

## Release Notes

 - New features:
   - added SQL file import into Query and Snippet tabs
   - added SQL file export from Query and Snippet tabs
   - query tab title now displays the name of the imported file
   - query history can now be filtered by database
   - added MySQL and MariaDB support in database Schema editor
   - new autocomplete in SQL code editor
   - added search and replace in SQL code editor
   - added live query execution timer for long-running queries
   - make "restore application tabs" behavior configurable in application settings
   - make DB object tree "scroll into view" behavior configurable in application settings

 - Major Bugs fixed:
   - fixed database tab restore concurrency issues when restoring multiple workspaces
   - change selected database when database child nodes are clicked
   - update workspace tooltips when corresponding connection gets renamed
   - don't try to run explain/analyze visualizer for non-Postgres database connections
   - don't allow setting nullable and primary-key column properties on schema editor
   - fixed various layout isues in UI walkthrough component
   - fixed issue when new monitoring widget modal wasn't possible to open after widget save/update
   - fixed automatic selection of last used database when reconnecting
   - reset connection properties form when connection manager dialog is closed

 - UI/UX Improvements:
   - improved application font size change handling various parts of the app
   - copy only selected text into clipboard if editor has a selection
   - application tabs now fit within a single row and can be scrolled if there are too many tabs
   - improved UI performance during application panel resize
   - improved UI responsiveness when application window is resized
   - application data grids layout improvements
   - data editor cell contents modal can now be shown by double-clicking the cell
   - database query tabs now show the associated database in tab title
   - added buttons for database tab scrolling
   - improved displaying of long error messages in application toast notifications
   - warn user about unsaved connection changes in connection manager dialog

 - Other Changes
   - code indent feature now has a maximum content length limited to 75mb
   - monitoring dashboard was rewritten in Vuejs
   - application tab management code was rewritten in Vuejs
   - password dialogs were rewritten in Vuejs
   - improved SSH tunnel error handling
   - improved error reporting when SSH tunnel issues occur
   - legacy code cleaned-up/removed
   - improved database back-end clean-up when query is cancelled by the user
   - updated django from 3.2.18 to 3.2.25
   - updated tabulator.js  from 5.5.2 to 6.2
   - updated chart.js
   - significantly improved application error logging


# PgManage 1.0 RC 1

## Release Date: Jan 4 2024

## Release Notes

 - New features:
   - new welcome screen which displays app shortcuts and recent connections list
   - added "run selection" feature in query editor
   - autocomplete setting is now stored separately for each DB connection
   - added SQLite3 support in table editor

 - Major Bugs fixed:
   - various layout fixes on snippets panel
   - fixed memory leak in snippets panel tree view
   - fixed postgres binary path corruption when pigz binary path is changed in settings dialog
   - added snippet and snippet folder name validation
   - added CSV delimiter validation in app settings
   - multiple fixes in Getting Started wizard
   - fixed query editor re-focusing when autocomplete widget closes
   - added connection group name validation
   - fixed disabled DB connection string input when creating new connection

 - UI/UX Improvements:
   - slightly improved app startup speed

 - Other Changes
   - improved error handling when app back-end is down or unavailable due to network issues
   - application data grids migrated from Handsontable to Tabulator.js
   - updated Vuejs and Bootstrap libraries


# PgManage 1.0 Beta 3

## Release Date: Nov 4 2023

## Release Notes

 - New features:
   - added UI for creating/altering DB tables (currently for Postgres only)
   - added new Entity Relationship Diagram for all supported databases
   - added PIGZ support for database backup and restore
   - added UI for PG Cron extension

 - Major Bugs fixed:
   - fixed the issue when "Test Connection" action fails on previously saved DB connection
   - fixed SQL autocomplete issues

 - UI/UX Improvements:
   - default TCP port in database connection form is now prepopulated based on selected database type
   - improved styling for Pev2 Query Explain component
   - major dark theme improvements
   - the data editor tab is rewritten in Vuejs with various UX improvements like revert changed, display number of changes made etc
   - the state of autocomplete toggle switch is now saved to application settings
   - in DB Query tab the Cancel Query button is now displayed for long running queries only (>1000ms)
   - various layout improvements on DB Query tab, application pane separators etc.
   - minimized UI visual clutter

 - Other Changes
   - database object tree was fully rewritten in Vuejs
   - moved SQL formatting/indentation to front-end
   - refactored DB Object APIs
   - JS assets are now managed with NPM and bundled with Vite
   - Long-polling code cleaned up and refactored
   - DB console tab was fully rewritten in Vuejs
   - DB query tab was fully rewritten in Vuejs


# PgManage 1.0 Beta 2

## Release Date: Jun 15 2023

## Release Notes

 - New features:
   - ability to disable CSV header when exporting data grid contents
   - added UI for Postgres extension management
   - new hierarchical connections menu
   - use random TCP port number for the application back-end process so Pgmanage does not occupy ports commonly used by other applications
   - ability to select SSL connection options in Connection Management dialog
   - remember and restore application window position and size when the app starts
   - added configurable date/time display format in the application settings dialog
   - restore the last used database and query tabs when pgmanage starts

 - Major Bugs fixed:
   - if the query entered by the user contains explain keyword, clicking on explain/analyze button will no longer prepend the query with an extra explain keyword (previously this bug resulted in syntactically incorrect query)

 - UI/UX Improvements:
    - ability to work with multiple databases within a DB session without needing to select the "active" database
    - if query entered by the user contains explain keyword, the explain tab will be opened automatically when user clicks the "Run query" button
    - explain and analyze buttons are now grouped together and separated from other query buttons
    - pre-set database connection TCP port in the Connection Management dialog based on selected database type
    - add visually matching themes for query editor

 - Other Changes
    - django has been updated from 2.2 to 3.2
    - bundled python version changed from 3.8 to 3.9
    - code clean-up and refactoring
    - moved application shared data into globally accessible Pinia store
    - replace cx_Oracle library with oracledb

# PgManage 1.0 Beta

## Release Date: Apr 20 2023

## Release Notes

- New features:
  - added backup/restore support for Postgres
  - first version of PgManage Handbook was published to https://pgmanage.readthedocs.io/en/latest

- Major Bugs fixed:
  - fixed .AppImage compatibility issues for newer Linux distributions which do not have libcrypt installed
  - added logic to terminate stale back-end process if the front-end process crashes
  - fixed application UI process memory leaks


- UI/UX Improvements:
  - improved support for configuration options search in Postgres Server Configuration Management
  - automatically readjust query editor font size when the application font size changes
  - various application layout and UI improvements
  - limited minimum application window size to 1024x766
  - fixed splash screen flickering/position issues during the application startup
  - add PgManage Handbook links to application error modal dialogs
  - improved handling of drag-and-drop reordering for database operations tabs

- Other Changes
  - added support for configurable Postgresql Client binary path in application settings
  - excluded SASS libraries and .sass files from the release builds
  - include EGL/GLES libraries into app release builds
  - pev2 upgraded to v1.7.0
  - removed "plugins" and other obsolete menu items from the application UI
  - removed unused files and dead code from the project
  - shred SSH keys stored in the app during the Master Password Reset

# PgManage 1.0 Alpha

## Release Date: Feb 21 2023

## Release Notes

- New features:
  - new connection management UI
  - added support for postgres server configuration management
  - new explain/analyze UI powered by pev2, including pev2 dark theme support
  - connection credential encryption
  - backported support for monitoring data-grid-based monitoring widgets
  - backported pie charts widgets for numbackends and database sizes
  - added password strength validation for user and master passwords
  - PostgreSQL 9.6, 10, 11, 12, 13, 14 and 15 support

- Major Bugs fixed:
  - fixed data export to csv/xls format in the desktop version of the app
  - added superuser permission check on all user management APIs
  - extra validations added to prevent creation of unnamed connection groups
  - fixed external links not working in the desktop variant of the app
  - fixed postgres special commands on postgresql versions 12 and higher
  - fixed broken postgres documentation links available in database tree view menus
  - made all web/cdn app dependencies local so pgmanage can work properly without an internet connection

- UI/UX Improvements:
  - reorganized connection management menus in the left menu bar
  - fixed DDL tab auto resizing
  - the top-right utilities menu now expands on click instead of mouse-hover
  - added DDL/properties tab resize limits to prevent it from becoming impossible to grab/resize back
  - unified tooltip appearance throughout the whole app
  - unified pictogram look and feel thoughout the whole app
  - improved database tree view navigation by adding smooth scroll to the newly expanded tree node. previously when some tree view node was expanded it jumped out of sight
  - improved data grid/table readability
  - improved database entity tree view readability
  - fixed date formatting in sql command history grid
  - fixed date formatting in db console command history grid
  - proper styling for dialog primary and secondary buttons. the secondary buttons in forms and dialogs were previously looked disable/grayed-out which was confusing.
  - the autocommit checkbox on query tab now stays visible despite of application window size
removed the option to make connections public in desktop variant of the app (which has only one user so shared/public connections make no sense)

- Other Changes
  - added postgresql 14 and 15  support
  - application data directory and db/log file naming was changed from omnidb* to pgmanage*.
