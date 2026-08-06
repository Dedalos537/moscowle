<?php
header('Content-Type: text/plain; charset=utf-8');
echo 'PHP '.phpversion()." OK\n";
echo 'disable_functions: '.ini_get('disable_functions')."\n";
echo "--- exec ---\n";
if (function_exists('exec')) { exec('id 2>&1; echo ===; whoami 2>&1; echo ===; pwd 2>&1', $o); echo implode("\n", $o)."\n"; }
else echo "exec DISABLED\n";
echo "--- shell_exec ---\n";
if (function_exists('shell_exec')) { echo shell_exec('id 2>&1'); } else echo "shell_exec DISABLED\n";
echo "--- proc_open ---\n";
if (function_exists('proc_open')) echo "proc_open exists\n"; else echo "proc_open DISABLED\n";
echo "--- system ---\n";
if (function_exists('system')) { system('id 2>&1'); } else echo "system DISABLED\n";
echo "--- open_basedir ---\n".ini_get('open_basedir')."\n";
?>
