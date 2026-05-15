import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

def visualize_kfold(k=5):
    # Setup plotting area
    fig, ax = plt.subplots(figsize=(10, 5))
    
    # Professional grayscale tones for document consistency
    train_color = '#e0e0e0'  # Light gray
    test_color = '#424242'   # Dark gray
    
    for i in range(k):
        # Y-coordinate (mapped from top to bottom)
        y = k - i
        
        # Iterate through each fold
        for j in range(k):
            # In iteration 'i', the j-th fold is the test set if i == j
            is_test = (i == j)
            color = test_color if is_test else train_color
            label_text = "TEST" if is_test else "TRAIN"
            text_color = "white" if is_test else "black"
            
            # Draw the block representing a data fold
            rect = plt.Rectangle((j, y), 0.85, 0.8, facecolor=color, edgecolor='black', linewidth=1)
            ax.add_patch(rect)
            
            # Add text labels inside the blocks
            ax.text(j + 0.425, y + 0.4, label_text, ha='center', va='center', 
                    color=text_color, fontsize=9, fontweight='bold')
            
        # Label each split/iteration on the left
        ax.text(-0.2, y + 0.4, f"Split {i+1}", va='center', ha='right', fontsize=10)

    # Clean up formatting
    ax.set_xlim(-1.5, k)
    ax.set_ylim(0.5, k + 1.5)
    ax.set_xticks(np.arange(k) + 0.425)
    ax.set_xticklabels([f"Fold {f}" for f in range(1, k+1)])
    ax.set_yticks([])
    
    # Hide axis spines for a cleaner "hand-drawn" skeletal look
    for spine in ['top', 'right', 'left', 'bottom']:
        ax.spines[spine].set_visible(False)
        
    ax.set_title(f"{k}-Fold Cross-Validation Strategy", fontsize=14, fontweight='bold', pad=20)
    
    # Add a legend for clarity
    legend_elements = [
        Patch(facecolor=train_color, edgecolor='black', label='Training Set (80%)'),
        Patch(facecolor=test_color, edgecolor='black', label='Validation Set (20%)')
    ]
    ax.legend(handles=legend_elements, loc='lower center', bbox_to_anchor=(0.5, -0.15), 
              ncol=2, frameon=False)
    
    plt.tight_layout()
    plt.savefig('kfold_validation_process.png', dpi=300)
    plt.show()

visualize_kfold(5)
