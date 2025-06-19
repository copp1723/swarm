#!/usr/bin/env python3
"""
Celery Monitoring Script
Provides real-time monitoring of Celery workers and tasks
"""

import time
import sys
import argparse
from datetime import datetime
from colorama import init, Fore, Style
from celery import Celery
from config.celery_config import celery_app

# Initialize colorama for cross-platform colored output
init()

def clear_screen():
    """Clear the terminal screen"""
    print("\033[H\033[J", end="")

def format_task_info(task):
    """Format task information for display"""
    return {
        'id': task.get('id', 'N/A')[:8],
        'name': task.get('name', 'Unknown').split('.')[-1],
        'args': str(task.get('args', []))[:30],
        'time': task.get('time_start', 'N/A')
    }

def monitor_workers(app, refresh_interval=2):
    """Monitor Celery workers and display status"""
    print(f"{Fore.GREEN}Starting Celery Monitor...{Style.RESET_ALL}")
    print(f"Refresh interval: {refresh_interval} seconds")
    print("Press Ctrl+C to exit\n")
    
    try:
        while True:
            clear_screen()
            
            # Header
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}MCP Multi-Agent Platform - Celery Monitor{Style.RESET_ALL}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
            
            # Get inspector
            inspector = app.control.inspect()
            
            # Active workers
            print(f"{Fore.GREEN}Active Workers:{Style.RESET_ALL}")
            active_workers = inspector.active()
            
            if active_workers:
                for worker, tasks in active_workers.items():
                    worker_name = worker.split('@')[0]
                    print(f"  {Fore.YELLOW}{worker_name}{Style.RESET_ALL} - {len(tasks)} active tasks")
                    for task in tasks[:5]:  # Show max 5 tasks per worker
                        info = format_task_info(task)
                        print(f"    └─ [{info['id']}] {info['name']} {info['args']}")
            else:
                print(f"  {Fore.RED}No active workers found{Style.RESET_ALL}")
            
            print()
            
            # Queue sizes
            print(f"{Fore.GREEN}Queue Status:{Style.RESET_ALL}")
            active_queues = inspector.active_queues()
            if active_queues:
                queue_summary = {}
                for worker, queues in active_queues.items():
                    for queue in queues:
                        queue_name = queue.get('name', 'unknown')
                        if queue_name not in queue_summary:
                            queue_summary[queue_name] = 0
                        queue_summary[queue_name] += 1
                
                for queue_name in sorted(queue_summary.keys()):
                    print(f"  {Fore.YELLOW}{queue_name}{Style.RESET_ALL}: Active on {queue_summary[queue_name]} worker(s)")
            else:
                print(f"  {Fore.RED}No active queues{Style.RESET_ALL}")
            
            print()
            
            # Task statistics
            print(f"{Fore.GREEN}Task Statistics:{Style.RESET_ALL}")
            stats = inspector.stats()
            if stats:
                total_tasks = 0
                for worker, worker_stats in stats.items():
                    if 'total' in worker_stats:
                        total_tasks += sum(worker_stats['total'].values())
                print(f"  Total processed: {total_tasks}")
            
            # Reserved tasks
            reserved = inspector.reserved()
            if reserved:
                total_reserved = sum(len(tasks) for tasks in reserved.values())
                print(f"  Reserved tasks: {total_reserved}")
            
            # Scheduled tasks
            scheduled = inspector.scheduled()
            if scheduled:
                total_scheduled = sum(len(tasks) for tasks in scheduled.values())
                print(f"  Scheduled tasks: {total_scheduled}")
            
            print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.GRAY}Refreshing in {refresh_interval} seconds...{Style.RESET_ALL}")
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Monitoring stopped.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}Error: {e}{Style.RESET_ALL}")
        sys.exit(1)

def show_task_history(app, limit=20):
    """Show recent task history"""
    print(f"{Fore.GREEN}Recent Task History:{Style.RESET_ALL}")
    
    # This would typically query your result backend
    # For now, showing what we can get from workers
    inspector = app.control.inspect()
    
    # Get registered tasks
    registered = inspector.registered()
    if registered:
        print(f"\n{Fore.YELLOW}Registered Tasks:{Style.RESET_ALL}")
        all_tasks = set()
        for worker, tasks in registered.items():
            all_tasks.update(tasks)
        
        for task in sorted(all_tasks):
            print(f"  - {task}")
    
    # Get active tasks
    active = inspector.active()
    if active:
        print(f"\n{Fore.YELLOW}Currently Active Tasks:{Style.RESET_ALL}")
        for worker, tasks in active.items():
            if tasks:
                print(f"\n  Worker: {worker}")
                for task in tasks:
                    info = format_task_info(task)
                    print(f"    [{info['id']}] {info['name']}")

def main():
    parser = argparse.ArgumentParser(description='Monitor Celery workers and tasks')
    parser.add_argument(
        '--mode',
        choices=['monitor', 'history'],
        default='monitor',
        help='Monitoring mode'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=2,
        help='Refresh interval in seconds (for monitor mode)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of tasks to show (for history mode)'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'monitor':
        monitor_workers(celery_app, args.interval)
    elif args.mode == 'history':
        show_task_history(celery_app, args.limit)

if __name__ == '__main__':
    main()