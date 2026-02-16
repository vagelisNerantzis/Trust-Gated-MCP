import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import sys

def generate_visualizations(log_path, output_dir):
    if not os.path.exists(log_path):
        print(f"Error: Log file not found at {log_path}")
        return

    df = pd.read_csv(log_path)
    
    # Ensure output dir exists
    os.makedirs(output_dir, exist_ok=True)

    # --- 1. Trust Score Plot ---
    plt.figure(figsize=(10, 6))
    sns.set_style("whitegrid")
    
    # Plot each scenario
    sns.lineplot(data=df, x='day', y='trust_score', hue='scenario_id', marker='o')
    
    plt.title('Trust Score Evolution per Scenario (V3)')
    plt.xlabel('Day')
    plt.ylabel('Trust Score')
    plt.ylim(-0.05, 1.05)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    plot_path = os.path.join(output_dir, 'trust_score_plot.png')
    plt.savefig(plot_path)
    print(f"Generated Plot: {plot_path}")
    plt.close()

    # --- 2. Summary Table ---
    # Per-scenario summary
    summary = df.groupby('scenario_id').agg({
        'trust_score': ['min', 'max', 'last'],
        'override': 'sum',
        'executed_action': lambda x: (x == 'ACT_UNRESTRICTED').sum()
    })
    
    # Flatten columns
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.rename(columns={
        'trust_score_min': 'Min Trust',
        'trust_score_max': 'Max Trust',
        'trust_score_last': 'Final Trust',
        'override_sum': 'Overrides',
        'executed_action_<lambda>': 'Restricted Actions'
    })
    
    # Add count of total steps
    summary['Total Steps'] = df.groupby('scenario_id').size()
    
    table_path = os.path.join(output_dir, 'summary_table.md')
    with open(table_path, 'w') as f:
        f.write("# V3 Experiment Summary\n\n")
        f.write(summary.to_markdown())
        f.write("\n\n")
        f.write(f"**Total Scenarios:** {len(summary)}\n")
        f.write(f"**Total Steps:** {summary['Total Steps'].sum()}\n")
    
    print(f"Generated Table: {table_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_path = sys.argv[1]
    else:
        log_path = "logs/runs/experiment_log.csv"
        
    # Default to same dir as logs
    output_dir = os.path.dirname(log_path)
    
    generate_visualizations(log_path, output_dir)
