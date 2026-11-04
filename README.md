# Audax Data Manager
*(formerly PgManage)*

![Audax Data Manager Banner](/artwork/readme_banner.png)

**Audax Data Manager** is a free, open-source database client and administration tool
for PostgreSQL, MySQL, MariaDB, SQL Server, SQLite, and Oracle - all from one app, so
you don't need a different tool per database. It's a database manager that does not get
in your way.

- **One Client, Six Databases:** PostgreSQL, MySQL, MariaDB, SQL Server, SQLite, and
  Oracle - no more switching tools per engine.
- **Free & Open Source (MIT License).** No license fees, source available on GitHub.
- **Privacy-First:** zero tracking, zero telemetry - we respect our users.
- **Actively Developed:** a new release every 6–8 weeks.
- **Trusted by the Community:** 1,100+ GitHub stars and 8,000+ downloads.

![Audax Data Manager Showcase](/artwork/showcase.gif)

[![Static Badge](https://img.shields.io/badge/DOWNLOAD-geen?style=for-the-badge&logo=github&logoColor=white&color=green)](https://github.com/commandprompt/audax-data-manager/releases)
[![Static Badge](https://img.shields.io/badge/DISCORD-grey?style=for-the-badge&logo=discord&logoColor=white&color=%235865F2)](https://discord.gg/FvweAhhUeu)

# ⚡ Supported Databases
<img src="https://cdn.simpleicons.org/postgresql/000/fff#1" alt="postgresql" width=19 height=19> **PostgreSQL**
&nbsp;&nbsp;<img src="https://cdn.simpleicons.org/mariadb/000/fff#1" alt="mariadb" width=19 height=19> **MariaDB**
&nbsp;&nbsp;<img src="https://cdn.simpleicons.org/mysql/000/fff#1" alt="mysql" width=19 height=19> **MySQL**
&nbsp;&nbsp;<img src="https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/microsoftsqlserver.svg" alt="sql server" width=19 height=19> **SQL Server**
&nbsp;&nbsp;<img src="https://cdn.simpleicons.org/sqlite/000/fff#1" alt="sqlite" width=19 height=19> **SQLite**
&nbsp;&nbsp;<img src="https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/oracle.svg" alt="oracle" width=19 height=19> **Oracle**

# ✨ Features
**Multiple Workspaces:** connect to and manage multiple databases at once in a clean, tabbed interface.  
**Smart Autocomplete:** schema- and context-aware suggestions for tables, views, columns, aliases, and functions as you type.  
**Powerful SQL Editor:** syntax highlighting, code folding, and inline error annotations pointing right at the problem.  
**Visual Query Plans:** run queries and visualize execution plans alongside a spreadsheet-like results grid.  
**Data & Schema Editors:** browse and edit records, and create or modify tables, all visually.  
**Entity Relationship Diagrams:** view table relationships as an ERD.  
**Fuzzy Search:** jump straight to any database object without manual drill-down.  
**Live Monitoring:** view real-time performance graphs, with support for custom widgets.  
**Postgres Config Management:** search and tweak server parameters, with snapshots to track changes.  
**Background Backup & Restore:** back up or restore your Postgres cluster without blocking your work.  
**Secure by Design:** credentials encrypted behind a Master Password, plus SSH tunneling and a built-in SSH terminal for direct server access.  
**Dark or Light:** choose the theme (and UI scale) that suits you.  

# 📦 Install
Audax Data Manager works on **Linux** **macOS** and **Windows** platforms: https://github.com/commandprompt/audax-data-manager/releases

# 📚 Documentation
**Full Documentation**: https://audax.readthedocs.io/

# 🧩 Contribute
**Contributing to Audax Data Manager is easy.**  
⭐ Support Audax Data Manager by giving it a star. Thanks!

We love your input! We want to make contributing to this project as easy and
transparent as possible, whether it's:
- [Reporting a bug, proposing a feature](https://github.com/commandprompt/audax-data-manager/issues/new)
- [Asking questions, discussing the current state of the code](https://github.com/commandprompt/audax-data-manager/discussions/new)

Pull-requests are welcome, please read [Development.md](DEVELOPMENT.MD) for instructions on how to spin-up your local dev copy of the project.  
Contribute to Audax Data Manager Handbook by opening a [pull-request](https://github.com/commandprompt/pgmanage-docs/pulls) in the corresponding project.  

**Write bug reports with detail.**

Great Bug Reports tend to have:
* A quick summary and/or background
* Audax Data Manager version
* Operating system and version
* Steps to reproduce
* Be specific!
* What you expected would happen
* What actually happens
* Notes (possibly including why you think this might be happening, or stuff you tried that didn't work)

# 🪵 Changelog
[CHANGELOG.md](CHANGELOG.md)

# 🍰 Credits
Audax Data Manager is being developed by [Command Prompt, Inc.](https://www.commandprompt.com/).  
We proudly leverage all of the great work done by the original (now dormant) project [OmniDB](https://github.com/OmniDB/OmniDB).  

Built with [Django](https://www.djangoproject.com/) on the backend and [Vue.js](https://vuejs.org/) on the frontend.  

Postgres query plan visualization is powered by [Pev2](https://github.com/dalibo/pev2).  
Entity Relationship Diagrams are powered by [Vue Flow](https://vueflow.dev/).  
SQL query generation in Schema editor is powered by [Knex.js](https://knexjs.org).  
SQL code completion is powered by [ANTLR](https://www.antlr.org/).  
Data tables handled by an awesome [Tabulator.js](https://tabulator.info/) library.  
Database console and builtin SSH terminal are powered by [xterm.js](https://xtermjs.org/).  
