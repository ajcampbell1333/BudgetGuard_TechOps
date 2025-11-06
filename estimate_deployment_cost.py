#!/usr/bin/env python3
"""
Quick script to estimate deployment costs for NIM nodes

This shows the cost of JUST deploying (not running) a NIM instance.
"""

from deployment.cost_estimator import CostEstimator

def main():
    estimator = CostEstimator()
    
    print("=" * 70)
    print("NIM Node Deployment Cost Estimation")
    print("=" * 70)
    print("\nNOTE: Deployment itself (creating infrastructure) is FREE")
    print("Costs below are for RUNNING the container (per hour)")
    print("=" * 70)
    print()
    
    # Example node
    node_type = "FLUX Dev"
    
    print(f"Estimating costs for: {node_type}")
    print("-" * 70)
    print()
    
    # Get estimates for 1 hour of runtime
    for provider in ["aws", "azure", "gcp"]:
        try:
            estimate = estimator.estimate_deployment_cost(node_type, provider, duration_hours=1.0)
            
            print(f"{estimate['provider']}:")
            print(f"  Deployment Cost: ${estimate['deployment_cost']:.4f} (FREE)")
            print(f"  Running Cost (1 hour): ${estimate['hourly_cost']:.4f}")
            print(f"  Resources: {estimate['resources']['cpu']} vCPU, {estimate['resources']['memory_gb']}GB RAM")
            if estimate['resources']['gpu']:
                print(f"  GPU: Yes (included in cost)")
            print()
        except Exception as e:
            print(f"{provider.upper()}: Error - {e}")
            print()
    
    # Show comparison
    print("-" * 70)
    print("Provider Comparison:")
    print("-" * 70)
    
    comparison = estimator.compare_providers(node_type, duration_hours=1.0)
    
    if comparison['cheapest_provider']:
        print(f"\nCheapest provider for {node_type}: {comparison['cheapest_provider'].upper()}")
        print(f"Cost: ${comparison['cheapest_cost']:.4f} per hour")
        print("\nSavings vs other providers:")
        for provider, savings in comparison['savings'].items():
            print(f"  vs {provider.upper()}: ${savings:.4f}/hour")
    
    print()
    print("=" * 70)
    print("KEY TAKEAWAY:")
    print("Deployment (creating the service) costs: $0.00")
    print("You only pay when the container is RUNNING")
    print("=" * 70)

if __name__ == '__main__':
    main()

