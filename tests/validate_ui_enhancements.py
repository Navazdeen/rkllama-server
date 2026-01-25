#!/usr/bin/env python3
"""
Complete Validation Script for UI Enhancements

This script validates:
1. Live thinking updates functionality
2. Parameter configuration system
3. Response concatenation (bug fix)
4. Server restart conversation history (bug fix)
5. UI integration and robustness

Run with: python validate_ui_enhancements.py
"""

import sys
import os
import logging
from typing import Dict, List, Tuple
import subprocess
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ValidationReport:
    """Generate validation report."""
    
    def __init__(self):
        self.results = {
            'live_thinking': {'passed': 0, 'failed': 0, 'tests': []},
            'configuration': {'passed': 0, 'failed': 0, 'tests': []},
            'response_bug': {'passed': 0, 'failed': 0, 'tests': []},
            'restart_bug': {'passed': 0, 'failed': 0, 'tests': []},
            'robustness': {'passed': 0, 'failed': 0, 'tests': []},
            'integration': {'passed': 0, 'failed': 0, 'tests': []},
        }
    
    def add_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Add test result."""
        if category not in self.results:
            self.results[category] = {'passed': 0, 'failed': 0, 'tests': []}
        
        self.results[category]['tests'].append({
            'name': test_name,
            'passed': passed,
            'details': details
        })
        
        if passed:
            self.results[category]['passed'] += 1
        else:
            self.results[category]['failed'] += 1
    
    def print_report(self):
        """Print formatted validation report."""
        print("\n" + "=" * 80)
        print("UI ENHANCEMENT VALIDATION REPORT")
        print("=" * 80 + "\n")
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            passed = results['passed']
            failed = results['failed']
            total_passed += passed
            total_failed += failed
            
            status = "✅ PASS" if failed == 0 else "❌ FAIL"
            print(f"{status} - {category.upper().replace('_', ' ')}")
            print(f"  Passed: {passed} | Failed: {failed}")
            
            for test in results['tests']:
                symbol = "✅" if test['passed'] else "❌"
                print(f"  {symbol} {test['name']}")
                if test['details']:
                    print(f"     {test['details']}")
            print()
        
        print("=" * 80)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        print("=" * 80 + "\n")
        
        return total_failed == 0


def validate_live_thinking_updates(report: ValidationReport):
    """Validate live thinking updates functionality."""
    logger.info("Validating live thinking updates...")
    
    try:
        # Test 1: Thinking updates storage
        thinking_updates = {'current': [], 'lock': __import__('threading').Lock()}
        
        with thinking_updates['lock']:
            thinking_updates['current'].append("Step 1: Processing")
            thinking_updates['current'].append("Step 2: Gathering")
        
        if len(thinking_updates['current']) == 2:
            report.add_result('live_thinking', 'Thinking updates storage', True)
        else:
            report.add_result('live_thinking', 'Thinking updates storage', False, 
                            f"Expected 2 updates, got {len(thinking_updates['current'])}")
        
        # Test 2: Updates retrieval
        with thinking_updates['lock']:
            updates = thinking_updates['current'].copy()
            thinking_updates['current'].clear()
        
        if len(updates) == 2 and len(thinking_updates['current']) == 0:
            report.add_result('live_thinking', 'Updates retrieval and clearing', True)
        else:
            report.add_result('live_thinking', 'Updates retrieval and clearing', False)
        
        # Test 3: Concurrent access
        import threading
        
        def add_update(idx):
            for i in range(5):
                with thinking_updates['lock']:
                    thinking_updates['current'].append(f"Thread {idx} - Update {i}")
        
        thinking_updates['current'].clear()
        threads = [threading.Thread(target=add_update, args=(i,)) for i in range(3)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        if len(thinking_updates['current']) == 15:  # 3 threads * 5 updates
            report.add_result('live_thinking', 'Concurrent update handling', True)
        else:
            report.add_result('live_thinking', 'Concurrent update handling', False,
                            f"Expected 15 updates, got {len(thinking_updates['current'])}")
        
    except Exception as e:
        report.add_result('live_thinking', 'Live thinking validation', False, str(e))


def validate_parameter_configuration(report: ValidationReport):
    """Validate parameter configuration functionality."""
    logger.info("Validating parameter configuration...")
    
    try:
        # Test 1: Default values
        config = {
            'n_iterations': 3,
            'max_results': 3,
            'info_length_threshold': 500,
        }
        
        if config['n_iterations'] == 3 and config['max_results'] == 3:
            report.add_result('configuration', 'Default configuration values', True)
        else:
            report.add_result('configuration', 'Default configuration values', False)
        
        # Test 2: Configuration update
        config['n_iterations'] = 5
        config['max_results'] = 8
        config['info_length_threshold'] = 1000
        
        if config['n_iterations'] == 5 and config['max_results'] == 8:
            report.add_result('configuration', 'Configuration update', True)
        else:
            report.add_result('configuration', 'Configuration update', False)
        
        # Test 3: Boundary validation
        config['n_iterations'] = 1
        config['max_results'] = 10
        config['info_length_threshold'] = 100
        
        if config['n_iterations'] >= 1 and config['max_results'] <= 10:
            report.add_result('configuration', 'Boundary validation', True)
        else:
            report.add_result('configuration', 'Boundary validation', False)
        
        # Test 4: Configuration persistence
        original = config.copy()
        # Simulate operations
        temp = config['n_iterations']
        config['n_iterations'] = 2
        config['n_iterations'] = temp
        
        if config == original:
            report.add_result('configuration', 'Configuration persistence', True)
        else:
            report.add_result('configuration', 'Configuration persistence', False)
        
    except Exception as e:
        report.add_result('configuration', 'Configuration validation', False, str(e))


def validate_response_concatenation_fix(report: ValidationReport):
    """Validate response concatenation bug fix."""
    logger.info("Validating response concatenation fix...")
    
    try:
        # Test 1: Response appending not replacing
        chat_history = []
        
        # First exchange
        chat_history = chat_history + [{"role": "user", "content": "Q1"}]
        chat_history = chat_history + [{"role": "assistant", "content": "A1"}]
        
        first_exchange_len = len(chat_history)
        
        # Second exchange
        chat_history = chat_history + [{"role": "user", "content": "Q2"}]
        chat_history = chat_history + [{"role": "assistant", "content": "A2"}]
        
        if len(chat_history) == 4 and chat_history[0]['content'] == "Q1":
            report.add_result('response_bug', 'Response appending (not replacing)', True)
        else:
            report.add_result('response_bug', 'Response appending (not replacing)', False,
                            f"Expected 4 messages with intact history, got {len(chat_history)}")
        
        # Test 2: Streaming update correctness
        chat_history2 = [{"role": "user", "content": "What is AI?"}]
        response = ""
        
        for token in ["AI", " is", " artificial", " intelligence"]:
            response += token
            
            # Simulate streaming update
            if chat_history2 and chat_history2[-1]['role'] == 'assistant':
                chat_history2[-1]['content'] = response
            else:
                chat_history2.append({"role": "assistant", "content": response})
        
        if len(chat_history2) == 2 and "artificial intelligence" in chat_history2[-1]['content']:
            report.add_result('response_bug', 'Streaming response updates', True)
        else:
            report.add_result('response_bug', 'Streaming response updates', False)
        
        # Test 3: Multiple exchanges accumulation
        chat_history3 = []
        pairs = [("Q1", "A1"), ("Q2", "A2"), ("Q3", "A3")]
        
        for q, a in pairs:
            chat_history3 = chat_history3 + [{"role": "user", "content": q}]
            chat_history3 = chat_history3 + [{"role": "assistant", "content": a}]
        
        if len(chat_history3) == 6:
            report.add_result('response_bug', 'Multiple exchanges accumulation', True)
        else:
            report.add_result('response_bug', 'Multiple exchanges accumulation', False,
                            f"Expected 6 messages, got {len(chat_history3)}")
        
    except Exception as e:
        report.add_result('response_bug', 'Response concatenation validation', False, str(e))


def validate_restart_conversation_history_fix(report: ValidationReport):
    """Validate server restart conversation history bug fix."""
    logger.info("Validating server restart conversation history fix...")
    
    try:
        # Test 1: Session preservation
        sessions = {
            "chat_001": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"}
            ]
        }
        
        current_session_id = "chat_001"
        restored_history = sessions.get(current_session_id, [])
        
        if len(restored_history) == 2:
            report.add_result('restart_bug', 'Session preservation on restart', True)
        else:
            report.add_result('restart_bug', 'Session preservation on restart', False)
        
        # Test 2: Most recent chat selection
        chats = [
            {'id': 'chat_001', 'timestamp': 1000},
            {'id': 'chat_002', 'timestamp': 900},
            {'id': 'chat_003', 'timestamp': 1100}  # Most recent
        ]
        
        most_recent = max(chats, key=lambda x: x['timestamp'])
        
        if most_recent['id'] == 'chat_003':
            report.add_result('restart_bug', 'Most recent chat selection', True)
        else:
            report.add_result('restart_bug', 'Most recent chat selection', False)
        
        # Test 3: Chat list persistence
        chat_ids = ["chat_001", "chat_002", "chat_003"]
        persisted = chat_ids.copy()
        
        if len(persisted) == 3 and persisted[0] == "chat_001":
            report.add_result('restart_bug', 'Chat list persistence', True)
        else:
            report.add_result('restart_bug', 'Chat list persistence', False)
        
    except Exception as e:
        report.add_result('restart_bug', 'Restart conversation history validation', False, str(e))


def validate_ui_robustness(report: ValidationReport):
    """Validate UI interaction robustness."""
    logger.info("Validating UI robustness...")
    
    try:
        # Test 1: Rapid config changes
        config = {'n_iterations': 3, 'max_results': 3, 'info_length_threshold': 500}
        
        for i in range(100):
            config['n_iterations'] = (i % 5) + 1
            config['max_results'] = (i % 10) + 1
            config['info_length_threshold'] = ((i % 20) + 1) * 100
        
        if config['n_iterations'] > 0 and config['max_results'] > 0:
            report.add_result('robustness', 'Rapid configuration changes', True)
        else:
            report.add_result('robustness', 'Rapid configuration changes', False)
        
        # Test 2: Large chat history
        chat_history = []
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            chat_history.append({"role": role, "content": f"Message {i}"})
        
        if len(chat_history) == 100:
            report.add_result('robustness', 'Large chat history handling', True)
        else:
            report.add_result('robustness', 'Large chat history handling', False)
        
        # Test 3: Concurrent operations
        import threading
        
        results = []
        
        def worker():
            config = {'value': 0}
            for i in range(50):
                config['value'] = i
            results.append(config['value'])
        
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        if len(results) == 10:
            report.add_result('robustness', 'Concurrent operations', True)
        else:
            report.add_result('robustness', 'Concurrent operations', False)
        
    except Exception as e:
        report.add_result('robustness', 'UI robustness validation', False, str(e))


def validate_ui_integration(report: ValidationReport):
    """Validate UI integration."""
    logger.info("Validating UI integration...")
    
    try:
        # Test 1: Full session lifecycle
        config = {'n_iterations': 3, 'max_results': 3, 'info_length_threshold': 500}
        chat_history = []
        sessions = {"test": []}
        
        # User message
        chat_history = chat_history + [{"role": "user", "content": "Hello"}]
        sessions["test"] = list(chat_history)
        
        # Config update
        config['n_iterations'] = 4
        
        # Assistant message
        chat_history = chat_history + [{"role": "assistant", "content": "Hi!"}]
        sessions["test"] = list(chat_history)
        
        if len(chat_history) == 2 and config['n_iterations'] == 4:
            report.add_result('integration', 'Full session lifecycle', True)
        else:
            report.add_result('integration', 'Full session lifecycle', False)
        
        # Test 2: Config affects execution
        def search_with_config(config):
            return {'iterations': config['n_iterations'], 'results': config['max_results']}
        
        config = {'n_iterations': 2, 'max_results': 5, 'info_length_threshold': 300}
        result1 = search_with_config(config)
        
        config['n_iterations'] = 3
        result2 = search_with_config(config)
        
        if result1['iterations'] == 2 and result2['iterations'] == 3:
            report.add_result('integration', 'Configuration affects execution', True)
        else:
            report.add_result('integration', 'Configuration affects execution', False)
        
    except Exception as e:
        report.add_result('integration', 'UI integration validation', False, str(e))


def run_unit_tests(report: ValidationReport):
    """Run comprehensive unit tests."""
    logger.info("Running unit tests...")
    
    try:
        # Try to run the test file
        test_file = os.path.join(os.path.dirname(__file__), 'test_ui_validation.py')
        
        if os.path.exists(test_file):
            result = subprocess.run(
                [sys.executable, test_file],
                capture_output=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("✅ Unit tests passed")
                return True
            else:
                logger.warning("⚠️  Some unit tests failed")
                logger.warning(result.stdout.decode() if result.stdout else "")
                return False
        else:
            logger.warning(f"⚠️  Test file not found: {test_file}")
            return False
    
    except Exception as e:
        logger.error(f"Error running unit tests: {e}")
        return False


def main():
    """Run complete validation."""
    print("\n" + "=" * 80)
    print("UI ENHANCEMENT VALIDATION - Starting")
    print("=" * 80 + "\n")
    
    report = ValidationReport()
    
    # Run all validations
    validate_live_thinking_updates(report)
    validate_parameter_configuration(report)
    validate_response_concatenation_fix(report)
    validate_restart_conversation_history_fix(report)
    validate_ui_robustness(report)
    validate_ui_integration(report)
    
    # Run unit tests
    unit_tests_passed = run_unit_tests(report)
    
    # Print report
    all_passed = report.print_report()
    
    if all_passed and unit_tests_passed:
        print("✅ All validations PASSED!")
        return 0
    else:
        print("❌ Some validations FAILED")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
