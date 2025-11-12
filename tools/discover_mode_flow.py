"""
Discovery script to verify Mode and SearchMode parameter flow
Traces execution to verify API vs Browser mode selection and endpoint usage
"""
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def discover_mode_flow():
    """
    Discover and log the execution flow for different Mode/SearchMode combinations
    """
    print("="*70)
    print("MODE FLOW DISCOVERY")
    print("="*70)
    print()
    
    from src.interfaces.cli import _setup_client_connection
    from src.core.client import PerplexityClient
    from src.core.models import SearchMode
    
    # Test different scenarios
    scenarios = [
        {
            'name': 'API Mode - Default (no params)',
            'mode': 'api',
            'search_mode': 'search',
            'profile': None,
            'no_auto': False,
            'expected_mode': 'api'
        },
        {
            'name': 'API Mode - Research',
            'mode': 'api',
            'search_mode': 'research',
            'profile': None,
            'no_auto': False,
            'expected_mode': 'api',
            'expected_api_mode': 'research'  # Should map to deep_research -> "research"
        },
        {
            'name': 'API Mode - Labs',
            'mode': 'api',
            'search_mode': 'labs',
            'profile': None,
            'no_auto': False,
            'expected_mode': 'api',
            'note': 'Labs may not have API endpoint'
        },
        {
            'name': 'Browser Mode - Default (no_auto=True)',
            'mode': 'browser',
            'search_mode': 'search',
            'profile': None,
            'no_auto': True,
            'expected_mode': 'browser'
        },
        {
            'name': 'Browser Mode - Research (no_auto=True)',
            'mode': 'browser',
            'search_mode': 'research',
            'profile': None,
            'no_auto': True,
            'expected_mode': 'browser'
        },
        {
            'name': 'Browser Mode - Labs (no_auto=True)',
            'mode': 'browser',
            'search_mode': 'labs',
            'profile': None,
            'no_auto': True,
            'expected_mode': 'browser'
        },
    ]
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'scenarios': {}
    }
    
    print("Testing connection setup scenarios...\n")
    
    for scenario in scenarios:
        print(f"[Testing] {scenario['name']}")
        print(f"  Mode: {scenario['mode']}")
        print(f"  SearchMode: {scenario['search_mode']}")
        print(f"  no_auto: {scenario['no_auto']}")
        
        try:
            client, use_browser_automation = _setup_client_connection(
                profile=scenario['profile'],
                no_auto=scenario['no_auto'],
                verbose=False  # Set to True for detailed logs
            )
            
            result = {
                'client_created': client is not None,
                'use_browser_automation': use_browser_automation,
                'actual_mode': 'browser' if (use_browser_automation or not client) else 'api',
                'expected_mode': scenario['expected_mode'],
                'match': False
            }
            
            if client:
                result['client_type'] = type(client).__name__
                result['has_cloudflare_bypass'] = hasattr(client, 'use_cloudflare_bypass')
                if hasattr(client, 'use_cloudflare_bypass'):
                    result['cloudflare_bypass_enabled'] = client.use_cloudflare_bypass
            
            result['match'] = (result['actual_mode'] == result['expected_mode'])
            
            status = "✓" if result['match'] else "✗"
            print(f"  {status} Result: Client={result['client_created']}, Browser={result['use_browser_automation']}")
            print(f"    Expected: {result['expected_mode']}, Actual: {result['actual_mode']}")
            
            # Test API mode mapping if applicable
            if result['actual_mode'] == 'api' and client and scenario['search_mode'] != 'labs':
                try:
                    from src.core.models import SearchMode
                    mode_map = {
                        'search': SearchMode.AUTO,
                        'research': SearchMode.DEEP_RESEARCH
                    }
                    if scenario['search_mode'] in mode_map:
                        search_mode_enum = mode_map[scenario['search_mode']]
                        # Check what API mode string this maps to
                        api_mode_map = {
                            SearchMode.AUTO: "concise",
                            SearchMode.PRO: "copilot",
                            SearchMode.REASONING: "reasoning",
                            SearchMode.DEEP_RESEARCH: "research"
                        }
                        api_mode = api_mode_map.get(search_mode_enum, "unknown")
                        result['api_mode_mapping'] = {
                            'search_mode': scenario['search_mode'],
                            'enum': search_mode_enum.value,
                            'api_mode_string': api_mode
                        }
                        print(f"    API Mode Mapping: {scenario['search_mode']} -> {api_mode}")
                except Exception as e:
                    result['api_mode_mapping_error'] = str(e)
            
            results['scenarios'][scenario['name']] = result
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results['scenarios'][scenario['name']] = {
                'error': str(e),
                'expected_mode': scenario.get('expected_mode', 'unknown')
            }
            import traceback
            results['scenarios'][scenario['name']]['traceback'] = traceback.format_exc()
        
        print()
    
    # Test API endpoint construction
    print("\n" + "="*70)
    print("API ENDPOINT VERIFICATION")
    print("="*70)
    print()
    
    try:
        from src.core.client import PerplexityClient
        from src.core.models import SearchConfig, SearchMode
        
        # Create a dummy client to test payload building
        dummy_client = PerplexityClient(cookies={})
        
        endpoint_tests = [
            {'search_mode': 'search', 'enum': SearchMode.AUTO, 'expected_api_mode': 'concise'},
            {'search_mode': 'research', 'enum': SearchMode.DEEP_RESEARCH, 'expected_api_mode': 'research'},
        ]
        
        results['api_endpoints'] = {}
        
        for test in endpoint_tests:
            config = SearchConfig(
                query="test query",
                mode=test['enum']
            )
            
            payload = dummy_client._build_search_payload(config)
            api_mode = payload['params']['mode']
            
            result = {
                'search_mode': test['search_mode'],
                'enum_value': test['enum'].value,
                'expected_api_mode': test['expected_api_mode'],
                'actual_api_mode': api_mode,
                'match': api_mode == test['expected_api_mode'],
                'endpoint': '/rest/sse/perplexity_ask',
                'payload_mode': api_mode
            }
            
            status = "✓" if result['match'] else "✗"
            print(f"{status} {test['search_mode']}: {test['enum'].value} -> API mode '{api_mode}'")
            print(f"    Expected: '{test['expected_api_mode']}', Got: '{api_mode}'")
            
            results['api_endpoints'][test['search_mode']] = result
        
        dummy_client.close()
        
    except Exception as e:
        print(f"✗ Error testing API endpoints: {str(e)}")
        results['api_endpoints_error'] = str(e)
        import traceback
        results['api_endpoints_traceback'] = traceback.format_exc()
    
    # Save results
    output_dir = Path(__file__).parent.parent / 'screenshots'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f'mode_flow_discovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    print("\nConnection Setup Results:")
    matches = 0
    total = 0
    for name, result in results['scenarios'].items():
        if 'error' not in result:
            total += 1
            if result.get('match', False):
                matches += 1
            status = "✓" if result.get('match', False) else "✗"
            print(f"  {status} {name}")
    
    print(f"\n  Total: {total}, Matches: {matches}, Mismatches: {total - matches}")
    
    if 'api_endpoints' in results:
        print("\nAPI Endpoint Mapping:")
        for mode, result in results['api_endpoints'].items():
            status = "✓" if result.get('match', False) else "✗"
            print(f"  {status} {mode}: {result.get('actual_api_mode', 'unknown')}")
    
    # Recommendations
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    
    issues = []
    if matches < total:
        issues.append(f"⚠ {total - matches} scenario(s) don't match expected behavior")
    
    if 'api_endpoints' in results:
        for mode, result in results['api_endpoints'].items():
            if not result.get('match', False):
                issues.append(f"⚠ API mode mapping for '{mode}' doesn't match expected")
    
    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  {issue}")
        print("\nAction required: Review and fix mode selection logic")
    else:
        print("\n✓ All tests passed - mode selection working correctly")
    
    return results


if __name__ == "__main__":
    try:
        discover_mode_flow()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

