"""
Sync live_signal_funnel.md and live_signal_funnel.csv with the audited runtime dataset.
"""

import csv
import shutil

shutil.copyfile("reports/live_signal_funnel_sequential.csv", "reports/live_signal_funnel.csv")
shutil.copyfile("reports/live_signal_funnel_sequential.md", "reports/live_signal_funnel.md")
print("✅ live_signal_funnel.csv and live_signal_funnel.md synced.")
