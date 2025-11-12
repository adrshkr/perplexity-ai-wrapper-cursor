"""
Perplexity AI Wrapper - CLI Interface

This module provides the command-line interface for the Perplexity AI Wrapper.
It handles both installed package and development mode imports automatically.
"""
import sys
import os
from pathlib import Path

# Setup imports for both installed and development modes
try:
    from src.utils.imports import setup_imports
    setup_imports()
except ImportError:
    # Fallback: manual setup if imports module not available
    cli_file = Path(__file__).resolve()
    if 'src' in str(cli_file.parent):
        project_root = cli_file.parent.parent.parent
        if project_root.exists() and (project_root / 'src').exists():
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))

import click
import json
import asyncio
import sys
import io
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown

# Fix encoding issues for all platforms
# Force UTF-8 encoding for consistent output across Windows, Linux, and WSL2
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
else:
    # Fallback for older Python versions
    import locale
    import os
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import core modules - try installed package first, then development mode
try:
    # Installed package mode (when installed via pip)
    from core.client import PerplexityClient
    from core.async_client import AsyncPerplexityClient
    from core.models import SearchMode, AIModel, SourceType, NetworkError
    from auth.cookie_manager import CookieManager
    from auth.account_generator import AccountGenerator
    from automation.web_driver import PerplexityWebDriver
    from utils.connection_manager import ConnectionManager
except ImportError:
    # Development mode (src.* imports)
    from src.core.client import PerplexityClient
    from src.core.async_client import AsyncPerplexityClient
    from src.core.models import SearchMode, AIModel, SourceType, NetworkError
    from src.auth.cookie_manager import CookieManager
    from src.auth.account_generator import AccountGenerator
    from src.automation.web_driver import PerplexityWebDriver
    from src.utils.connection_manager import ConnectionManager

console = Console()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _setup_client_connection(profile=None, no_auto=False, verbose=False, no_cloudflare_bypass=False, proxy_list=None):
    """
    Centralized client connection setup with fallback strategies.
    
    Returns:
        tuple: (client, use_browser_automation)
    """
    client = None
    use_browser_automation = False
    
    if profile:
        if not no_auto:
            if verbose:
                console.print(f"[cyan]Trying profile: {profile}...[/cyan]")
        connection_manager = ConnectionManager(verbose=verbose)
        client = connection_manager.setup_connection(profile=profile, skip_web_automation=True)
        
        if not client:
            console.print(f"[yellow]⚠ Profile '{profile}' not found or invalid - will use browser automation[/yellow]")
            use_browser_automation = True
        else:
            client = _configure_client_bypass(client, no_cloudflare_bypass, proxy_list)
            if not no_auto:
                console.print(f"[green]✓ Using profile: {profile}[/green]")
    elif not no_auto:
        if verbose:
            console.print("[cyan]Auto-detecting connection...[/cyan]")
        connection_manager = ConnectionManager(verbose=verbose)
        client = connection_manager.setup_connection(skip_web_automation=True)
        
        if client:
            client = _configure_client_bypass(client, no_cloudflare_bypass, proxy_list)
            if verbose:
                console.print("[green]✓ Connection established automatically[/green]")
                status = "Cloudflare bypass enabled" if (hasattr(client, 'use_cloudflare_bypass') and client.use_cloudflare_bypass) else "Direct API"
                console.print(f"[dim]Client status: {status}[/dim]")
        else:
            use_browser_automation = True
    else:
        use_browser_automation = True
    
    return client, use_browser_automation


def _configure_client_bypass(client, no_cloudflare_bypass=False, proxy_list=None):
    """Configure Cloudflare bypass settings on client"""
    if not hasattr(client, 'use_cloudflare_bypass'):
        return client
    
    if no_cloudflare_bypass:
        cookies = client.session.cookies.get_dict() if hasattr(client.session, 'cookies') else {}
        client = PerplexityClient(
            cookies=cookies,
            use_cloudflare_bypass=False,
            proxy_rotation=proxy_list
        )
    elif proxy_list and hasattr(client, 'bypass') and client.bypass:
        client.bypass.proxy_rotation = proxy_list
    
    return client


def _handle_cloudflare_error(e, query, search_mode_str, mode, model, sources, stream, output, format, profile, verbose, headless, keep_browser_open):
    """Handle Cloudflare blocking by falling back to browser automation"""
    error_msg = str(e)
    if "Cloudflare" in error_msg or "cloudflare" in error_msg.lower() or "403" in error_msg:
        if verbose:
            console.print("\n[yellow]⚠ API blocked - automatically switching to browser automation...[/yellow]")
        
        _smart_browser_search(
            query=query,
            search_mode_str=search_mode_str,
            mode=mode,
            model=model,
            sources=sources,
            stream=False,
            output=output,
            format=format,
            profile=profile,
            verbose=verbose,
            headless=headless,
            keep_browser_open=keep_browser_open
        )
        return True
    return False


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Perplexity AI Wrapper - API Client
    
    A comprehensive toolkit for interacting with Perplexity.ai
    
    Examples:
        perplexity -s "Tesla Flying cars"              # Simple search
        perplexity -d "Tesla Flying cars"              # Deep research
        perplexity -l "Create Tesla analysis project" # Labs project
        perplexity search "query" --mode pro           # Advanced search
    """
    pass


# ============================================================================
# SEARCH COMMANDS
# ============================================================================

@cli.command()
@click.argument('query', nargs=-1, required=True)
@click.option('--simple', '-s', is_flag=True, help='Simple search mode (default)')
@click.option('--deep', '-d', '--deep-research', is_flag=True, help='Deep research mode')
@click.option('--labs', '-l', is_flag=True, help='Labs mode (create projects)')
@click.option('--mode', '-m', type=click.Choice(['auto', 'pro', 'reasoning', 'deep_research']), 
              default=None, help='Search mode (overrides flags)')
@click.option('--model', type=str, help='AI model (e.g., gpt-4o, claude-3.7-sonnet)')
@click.option('--sources', multiple=True, help='Source types (web, scholar, social)')
@click.option('--stream', is_flag=True, help='Stream response')
@click.option('--output', '-o', type=click.Path(), help='Save output to file')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), 
              default='text', help='Output format')
@click.option('--profile', '-p', help='Cookie profile to use (optional - auto-detects if not provided)')
@click.option('--no-auto', is_flag=True, help='Disable automatic connection detection')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed connection attempts')
@click.option('--headless', is_flag=True, help='Run browser in headless mode (no browser window, terminal output only)')
@click.option('--keep-browser-open', '--interactive', is_flag=True, help='Keep browser open after search completes (browser visible, terminal output shown)')
@click.option('--no-cloudflare-bypass', is_flag=True, help='Disable cloudscraper Cloudflare bypass (use regular requests)')
@click.option('--proxy', multiple=True, help='Proxy URL(s) for rotation (e.g., --proxy http://proxy1:8080 --proxy http://proxy2:8080)')
def search(query, simple, deep, labs, mode, model, sources, stream, output, format, profile, no_auto, verbose, headless, keep_browser_open, no_cloudflare_bypass, proxy):
    """
    Execute a search query
    
    Examples:
        perplexity -s "Tesla Flying cars"              # Simple search
        perplexity -d "Tesla Flying cars"              # Deep research
        perplexity -l "Create Tesla analysis project" # Labs project
        perplexity "What is quantum computing?"        # Default search
        perplexity search "AI trends 2025" --mode pro --model gpt-4o
    """
    # Always show initial message
    # Join query words into single string
    query = ' '.join(query) if isinstance(query, tuple) else query
    
    # Determine mode based on flags (flags take precedence over --mode)
    if labs:
        search_mode_str = 'labs'
        console.print(f"\n[bold cyan]Labs Mode:[/bold cyan] {query}", style="bold")
    elif deep:
        search_mode_str = 'deep_research'
        console.print(f"\n[bold cyan]Deep Research:[/bold cyan] {query}", style="bold")
    elif simple:
        search_mode_str = 'auto'
        console.print(f"\n[bold cyan]Simple Search:[/bold cyan] {query}", style="bold")
    elif mode:
        search_mode_str = mode
        console.print(f"\n[bold cyan]Search Mode ({mode}):[/bold cyan] {query}", style="bold")
    else:
        search_mode_str = 'auto'  # Default
        console.print(f"\n[bold cyan]Searching:[/bold cyan] {query}", style="bold")
    
    # Smart connection management with automatic login
    # Strategy: Try API first, if fails or no cookies, use browser automation with persistent session
    proxy_list = list(proxy) if proxy else None
    
    if verbose:
        console.print("[dim]Connection strategy: Auto-detect -> Browser automation fallback[/dim]\n")
    
    client, use_browser_automation = _setup_client_connection(
        profile=profile,
        no_auto=no_auto,
        verbose=verbose,
        no_cloudflare_bypass=no_cloudflare_bypass,
        proxy_list=proxy_list
    )
    
    # If no valid API connection, use browser automation with persistent session
    if use_browser_automation or not client:
        # Use browser automation with persistent context for seamless login
        _smart_browser_search(
            query=query,
            search_mode_str=search_mode_str,
            mode=mode,
            model=model,
            sources=sources,
            stream=stream,
            output=output,
            format=format,
            profile=profile,
            verbose=verbose,
            headless=headless,
            keep_browser_open=keep_browser_open
        )
        return
    
    # Convert string inputs to enums (skip if labs mode)
    if search_mode_str != 'labs':
        search_mode = SearchMode(search_mode_str)
        ai_model = AIModel(model) if model else None
        source_types = [SourceType(s) for s in sources] if sources else None
    else:
        search_mode = None
        ai_model = None
        source_types = None
    
    try:
        # Show connection status (check actual state after initialization)
        if verbose:
            if hasattr(client, 'use_cloudflare_bypass'):
                status = "Cloudflare bypass enabled" if client.use_cloudflare_bypass else "Direct API (cloudflare bypass unavailable)"
            else:
                status = "Direct API"
            console.print(f"[dim]Using client: {status}[/dim]")
        
        # Handle Labs mode differently
        if search_mode_str == 'labs':
            console.print("\n[yellow]⚠ Labs Mode:[/yellow]")
            console.print("Labs API endpoint needs to be discovered.")
            console.print("Options:")
            console.print("1. Use browser automation (recommended)")
            console.print("2. Discover endpoint: python discover_endpoints.py")
            console.print("3. Use deep research instead: perplexity search -d \"your query\"\n")
            
            use_browser = console.input("Use browser automation? (y/N): ").lower() == 'y'
            
            if use_browser:
                console.print("\n[cyan]Opening browser...[/cyan]")
                # PerplexityWebDriver already imported at top
                
                driver = PerplexityWebDriver(headless=False, stealth_mode=True)
                try:
                    driver.start()
                    driver.navigate_to_perplexity()
                    
                    console.print("\n[yellow]Instructions:[/yellow]")
                    console.print("1. Click Labs icon (lightbulb) in browser")
                    console.print("2. Click 'New' button")
                    console.print("3. Enter your project description")
                    console.print("4. Wait for generation")
                    console.print("\nPress Enter when done...")
                    input()
                    
                    # Extract results
                    content = driver.get_page_content()
                    driver.save_screenshot("labs_project_result.png")
                    
                    console.print("\n[green]✓ Project created![/green]")
                    console.print(f"[green]✓ Screenshot saved: labs_project_result.png[/green]")
                    
                finally:
                    driver.close()
            else:
                # Try API endpoint (will likely fail)
                try:
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        console=console
                    ) as progress:
                        task = progress.add_task("Creating Labs project...", total=None)
                        
                        response = client.create_labs_project(query)
                        
                        progress.update(task, completed=True)
                    
                    # Display Labs response
                    _display_labs_response(response, format)
                    
                    # Save to file if specified
                    if output:
                        _save_output(response, output, format)
                        console.print(f"\n[green]✓ Saved to: {output}[/green]")
                except Exception as e:
                    console.print(f"\n[red]✗ Labs API Error: {str(e)}[/red]")
                    console.print("\n[yellow]💡 Recommendation:[/yellow]")
                    console.print("  Use browser automation or discover the endpoint:")
                    console.print("  python discover_endpoints.py")
        
        elif stream:
            # Streaming mode
            try:
                for chunk in client.search(
                    query=query,
                    mode=search_mode,
                    model=ai_model,
                    sources=source_types,
                    stream=True
                ):
                    content = chunk.get('content', '')
                    if content:
                        console.print(content, end='')
                console.print("\n")
            except (NetworkError, Exception) as e:
                if not _handle_cloudflare_error(e, query, search_mode_str, mode, model, sources, stream, output, format, profile, verbose, headless, keep_browser_open):
                    raise
        else:
            # Regular mode with spinner
            try:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Searching...", total=None)
                    
                    response = client.search(
                        query=query,
                        mode=search_mode,
                        model=ai_model,
                        sources=source_types,
                        stream=False
                    )
                    
                    progress.update(task, completed=True)
                
                # Display response
                _display_response(response, format)
                
                # Save to file if specified
                if output:
                    _save_output(response, output, format)
                    console.print(f"\n[green]✓ Saved to: {output}[/green]")
            
            except (NetworkError, Exception) as e:
                if not _handle_cloudflare_error(e, query, search_mode_str, mode, model, sources, stream, output, format, profile, verbose, headless, keep_browser_open):
                    raise
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        raise


@cli.command()
@click.option('--profile', '-p', help='Cookie profile to use')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed connection attempts')
def conversation(profile, verbose):
    """
    Start an interactive conversation session
    
    Example:
        perplexity conversation --profile my_account
    """
    # Automatic connection management
    client, _ = _setup_client_connection(profile=profile, no_auto=False, verbose=verbose)
    
    if not client:
        console.print("[yellow]⚠ Could not auto-detect connection, trying without auth...[/yellow]")
        client = PerplexityClient()
    conv_id = client.start_conversation()
    
    console.print("\n[bold green]Started Conversation[/bold green]")
    console.print("\n[yellow]Type your questions (or 'quit' to exit, 'export' to save)[/yellow]\n")
    
    try:
        while True:
            query = console.input("\n[bold cyan]You:[/bold cyan] ")
            
            if query.lower() in ['quit', 'exit', 'q']:
                break
            
            if query.lower() == 'export':
                export_format = console.input("Format (json/text/markdown): ") or 'text'
                export_data = client.export_conversation(format=export_format)
                filename = f"conversation_{conv_id[:8]}.{export_format}"
                with open(filename, 'w') as f:
                    f.write(export_data)
                console.print(f"[green]✓ Exported to: {filename}[/green]")
                continue
            
            if not query.strip():
                continue
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Thinking...", total=None)
                response = client.search(query, use_conversation=True)
                progress.update(task, completed=True)
            
            console.print(f"\n[bold magenta]Assistant:[/bold magenta]")
            console.print(response.answer)
            
            if response.sources:
                for idx, source in enumerate(response.sources[:3], 1):
                    console.print(f"  {idx}. {source.get('title', 'N/A')}")
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Conversation ended[/yellow]")
    
    # Offer to export
    if console.input("\nExport conversation? (y/N): ").lower() == 'y':
        export_format = console.input("Format (json/text/markdown): ") or 'text'
        export_data = client.export_conversation(format=export_format)
        filename = f"conversation_{conv_id[:8]}.{export_format}"
        with open(filename, 'w') as f:
            f.write(export_data)
        console.print(f"[green]✓ Exported to: {filename}[/green]")


@cli.command()
@click.argument('queries', nargs=-1)
@click.option('--mode', '-m', default='auto', help='Search mode')
@click.option('--output', '-o', type=click.Path(), help='Save results to file')
def batch(queries, mode, output):
    """
    Process multiple queries concurrently
    
    Example:
        perplexity batch "Query 1" "Query 2" "Query 3" --output results.json
    """
    if not queries:
        console.print("[red]No queries provided[/red]")
        return
    
    console.print(f"\n[bold]Processing {len(queries)} queries...[/bold]\n")
    
    async def run_batch():
        async with AsyncPerplexityClient() as client:
            with Progress(console=console) as progress:
                task = progress.add_task("Searching...", total=len(queries))
                
                responses = await client.batch_search(
                    list(queries),
                    mode=SearchMode(mode)
                )
                
                progress.update(task, completed=len(queries))
            
            return responses
    
    responses = asyncio.run(run_batch())
    
    # Display results
    table = Table(title="Batch Results")
    table.add_column("Query", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Answer Preview", style="white")
    
    for idx, (query, response) in enumerate(zip(queries, responses), 1):
        if isinstance(response, Exception):
            table.add_row(query, "[red]ERROR[/red]", str(response)[:50])
        else:
            table.add_row(query, "[green]✓[/green]", response.answer[:50] + "...")
    
    console.print(table)
    
    # Save if requested
    if output:
        results = []
        for query, response in zip(queries, responses):
            if not isinstance(response, Exception):
                results.append(response.to_dict())
        
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)
        console.print(f"\n[green]✓ Saved to: {output}[/green]")


# ============================================================================
# COOKIE MANAGEMENT COMMANDS
# ============================================================================

@cli.group()
def cookies():
    """Manage authentication cookies"""
    pass


@cookies.command('extract')
@click.option('--browser', '-b', type=click.Choice(['chrome', 'firefox', 'edge']), 
              default='chrome', help='Browser to extract from')
@click.option('--profile', '-p', help='Profile name to save as')
@click.option('--profile-path', help='Custom browser profile path (for Chrome: path to User Data folder)')
def extract_cookies(browser, profile, profile_path):
    """
    Extract cookies from browser
    
    Example:
        perplexity cookies extract --browser chrome --profile my_account
        perplexity cookies extract --browser chrome --profile my_account --profile-path "C:\\Users\\User\\AppData\\Local\\Google\\Chrome\\User Data"
    """
    console.print(f"\n[cyan]Extracting cookies from {browser}...[/cyan]")
    console.print("[yellow]⚠ Make sure your browser is completely closed![/yellow]")
    
    try:
        cookie_manager = CookieManager()
        
        # Use profile path if provided
        if profile_path and browser == 'chrome':
            cookies_dict = CookieManager.extract_from_chrome(profile_path=profile_path)
        else:
            cookies_dict = cookie_manager.auto_extract(browser=browser)
        
        if not cookies_dict:
            console.print("[red]✗ No cookies found for perplexity.ai[/red]")
            console.print("[yellow]Make sure you:[/yellow]")
            console.print("  1. Have visited https://www.perplexity.ai")
            console.print("  2. Are logged into your account")
            console.print("  3. Browser is completely closed")
            return
        
        console.print(f"[green]✓ Extracted {len(cookies_dict)} cookies[/green]")
        
        if profile:
            cookie_manager.save_cookies(cookies_dict, name=profile)
            console.print(f"[green]✓ Saved as profile: {profile}[/green]")
            console.print(f"\n[bold]You can now use:[/bold]")
            console.print(f"  perplexity search -s \"your query\" --profile {profile}")
        else:
            console.print("\n[yellow]Cookies (first 5):[/yellow]")
            for idx, (key, value) in enumerate(list(cookies_dict.items())[:5], 1):
                console.print(f"  {idx}. {key}: {value[:30]}...")
            console.print("\n[yellow]⚠ Cookies not saved! Use --profile to save them.[/yellow]")
    
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        console.print("\n[yellow]Troubleshooting:[/yellow]")
        console.print("  1. Close Chrome completely (check Task Manager)")
        console.print("  2. Make sure you're logged into Perplexity.ai")
        console.print("  3. Try manual cookie export (see MANUAL_COOKIE_EXPORT.md)")
        console.print("  4. Try Firefox or Edge instead")


@cookies.command('list')
def list_cookies():
    """List all saved cookie profiles"""
    cookie_manager = CookieManager()
    profiles = cookie_manager.list_profiles()
    
    if not profiles:
        console.print("[yellow]No saved profiles[/yellow]")
        return
    
    table = Table(title="Saved Cookie Profiles")
    table.add_column("Profile Name", style="cyan")
    table.add_column("Status", style="green")
    
    for profile in profiles:
        table.add_row(profile, "✓ Active")
    
    console.print(table)


@cookies.command('delete')
@click.argument('profile')
def delete_cookies(profile):
    """Delete a cookie profile"""
    cookie_manager = CookieManager()
    
    if cookie_manager.delete_profile(profile):
        console.print(f"[green]✓ Deleted profile: {profile}[/green]")
    else:
        console.print(f"[red]✗ Profile not found: {profile}[/red]")


# ============================================================================
# ACCOUNT GENERATION COMMANDS
# ============================================================================

@cli.group()
def account():
    """Account generation and management"""
    pass


@account.command('generate')
@click.option('--count', '-c', default=1, help='Number of accounts to generate')
@click.option('--emailnator-cookies', '-e', type=click.Path(exists=True), 
              help='Path to Emailnator cookies JSON')
@click.option('--delay', '-d', default=30, help='Delay between accounts (seconds)')
def generate_account(count, emailnator_cookies, delay):
    """
    Generate new Perplexity accounts
    
    Example:
        perplexity account generate --count 3 --emailnator-cookies cookies.json
    """
    if not emailnator_cookies:
        console.print("[red]✗ Emailnator cookies required[/red]")
        console.print("[yellow]Get them from: https://www.emailnator.com[/yellow]")
        return
    
    # Load emailnator cookies
    with open(emailnator_cookies, 'r') as f:
        en_cookies = json.load(f)
    
    console.print(f"\n[bold]Generating {count} account(s)...[/bold]\n")
    
    generator = AccountGenerator(
        emailnator_cookies=en_cookies,
        cookie_manager=CookieManager()
    )
    
    try:
        if count == 1:
            account = generator.create_account(save_profile=True)
            console.print(f"\n[green]✓ Account created: {account.email}[/green]")
        else:
            accounts = generator.create_multiple_accounts(count, delay=delay)
            console.print(f"\n[green]✓ Created {len(accounts)} accounts[/green]")
            
            # Show summary
            table = Table(title="Generated Accounts")
            table.add_column("Email", style="cyan")
            table.add_column("Status", style="green")
            
            for account in accounts:
                table.add_row(account.email, account.status)
            
            console.print(table)
    
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")


# ============================================================================
# WEB AUTOMATION COMMANDS
# ============================================================================

@cli.command()
@click.option('--headless', is_flag=True, help='Run in headless mode')
@click.option('--user-data-dir', type=click.Path(), help='Persistent browser profile directory (cookies persist automatically)')
@click.option('--profile', '-p', help='Cookie profile to use (one-time setup)')
@click.option('--persistent', is_flag=True, help='Use persistent context (auto-create profile directory)')
def browser(headless, user_data_dir, profile, persistent):
    """
    Start interactive browser session
    
    Examples:
        # One-time setup with cookies
        perplexity browser --profile my_account
        
        # Persistent context (recommended - cookies persist automatically)
        perplexity browser --persistent
        
        # Use existing persistent profile
        perplexity browser --user-data-dir browser_data/my_account
        
        # Headless mode
        perplexity browser --persistent --headless
    """
    console.print("\n[bold cyan]Starting browser session...[/bold cyan]")
    
    # Handle persistent context
    if persistent and not user_data_dir:
        from pathlib import Path
        profile_name = profile or "default"
        user_data_dir = f"browser_data/{profile_name}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Using persistent context: {user_data_dir}[/green]")
    
    # Load cookies if profile specified (for one-time setup)
    cookies = None
    if profile and not persistent:
        cookie_manager = CookieManager()
        cookies = cookie_manager.load_cookies(profile)
        if not cookies:
            console.print(f"[red]✗ Profile '{profile}' not found[/red]")
            console.print(f"[yellow]Available profiles: {', '.join(cookie_manager.list_profiles())}[/yellow]")
            return
        console.print(f"[green]✓ Loaded profile: {profile}[/green]")
    
    driver = PerplexityWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    # Set cookies BEFORE starting browser (will be injected into context before navigation)
    if cookies and not persistent:
        driver.set_cookies(cookies)
        console.print(f"[green]✓ Cookies loaded (will be injected before navigation)[/green]")
    
    try:
        driver.start()
        
        # Cookies are already injected in start() via _inject_cookies_into_context()
        driver.navigate_to_perplexity()
        
        if persistent:
            console.print("[yellow]💡 Tip: Log in once, cookies will persist automatically![/yellow]")
        
        console.print("\n[green]✓ Browser ready[/green]")
        console.print("[yellow]You can now use Perplexity.ai in the browser![/yellow]")
        if persistent:
            console.print("[green]✓ Using persistent context - your session will be saved[/green]")
        
        driver.interactive_mode()
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        if 'driver' in locals():
            driver.close()


@cli.command('browser-search')
@click.argument('query', nargs=-1, required=True)
@click.option('--profile', '-p', help='Cookie profile to use')
@click.option('--headless', is_flag=True, help='Run in headless mode')
@click.option('--output', '-o', type=click.Path(), help='Save output to file')
@click.option('--user-data-dir', type=click.Path(), help='Persistent browser profile directory')
@click.option('--persistent', is_flag=True, help='Use persistent context')
@click.option('--debug', is_flag=True, help='Enable network debugging and verbose output')
@click.option('--keep-browser-open', '--interactive', is_flag=True, help='Keep browser open after search completes')
@click.option('--extract-images', is_flag=True, help='Extract and save images from response')
@click.option('--image-dir', type=click.Path(), default='_resources', help='Directory to save images (default: _resources)')
@click.option('--export-markdown', is_flag=True, help='Export thread as Markdown file after search completes')
@click.option('--export-dir', type=click.Path(), help='Directory to save exported Markdown file (default: exports/)')
@click.option('--mode', '-m', type=click.Choice(['search', 'research', 'labs']), default='search', help='Search mode: search (default), research, or labs')
def browser_search(query, profile, headless, output, user_data_dir, persistent, debug, keep_browser_open, extract_images, image_dir, export_markdown, export_dir, mode):
    """
    Search using browser automation (bypasses Cloudflare)
    
    This uses browser automation to perform searches, which reliably bypasses
    Cloudflare protection. The browser window opens, performs the search,
    and extracts the response.
    
    Examples:
        perplexity browser-search "your search query"
        perplexity browser-search "your search query" --headless
        perplexity browser-search "your search query" --output answer.txt
        perplexity browser-search "your search query" --persistent
    """
    query = ' '.join(query) if isinstance(query, tuple) else query
    
    # Handle persistent context
    if persistent and not user_data_dir:
        from pathlib import Path
        profile_name = profile or "default"
        user_data_dir = f"browser_data/{profile_name}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Using persistent context: {user_data_dir}[/green]")
    
    # Load cookies if profile specified, or try default profile if no profile provided
    cookies = None
    cookie_manager = CookieManager()
    if profile and not persistent:
        cookies = cookie_manager.load_cookies(profile)
        if cookies and debug:
            console.print(f"[green]✓ Loaded profile: {profile}[/green]")
    elif not persistent:
        # Try to load default profile if no profile specified
        try:
            cookies = cookie_manager.load_cookies("default")
            if cookies and debug:
                console.print(f"[green]✓ Loaded default cookie profile[/green]")
        except Exception:
            # No default profile available - that's okay
            pass
    
    driver = PerplexityWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    # Set cookies BEFORE starting browser (will be injected into context before navigation)
    if cookies and not persistent:
        driver.set_cookies(cookies)
        if debug:
            console.print(f"[green]✓ Cookies loaded (will be injected before navigation)[/green]")
    
    # Platform detection (for any platform-specific handling if needed)
    platform_info = _get_platform_info()
    
    # Configure logging level based on debug flag
    if debug:
        import logging
        logging.getLogger('src.automation.web_driver').setLevel(logging.DEBUG)
        # Also configure root logger if needed
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    driver_initialized = False
    try:
        if debug:
            console.print("[cyan]Starting browser...[/cyan]")
            console.print("[dim]This may take 10-30 seconds (solving Cloudflare challenge)...[/dim]")
        
        # Show headless mode indicator
        if headless:
            console.print("[yellow]Running in headless mode (no browser window)[/yellow]")
            if debug:
                console.print("[dim]Headless mode uses virtual display - browser runs in background[/dim]")
        
        try:
            driver.start(debug_network=debug)
            driver_initialized = True
            if debug:
                console.print("[green]✓ Browser started successfully[/green]")
        except ImportError as import_error:
            console.print(f"[red]✗ Missing dependency: {import_error}[/red]")
            console.print("[yellow]💡 Try: pip install cloudscraper playwright[/yellow]")
            raise
        except Exception as start_error:
            console.print(f"[red]✗ Failed to start browser: {start_error}[/red]")
            console.print("[yellow]💡 Tip: Add --debug flag for detailed error information[/yellow]")
            if debug:
                import traceback
                console.print(f"\n[dim]Full traceback:[/dim]")
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            raise
        
        # Small delay to ensure browser is fully ready
        import time
        time.sleep(1)
        
        # Cookies are already injected in start() via _inject_cookies_into_context()
        if debug:
            console.print("[cyan]Navigating to Perplexity...[/cyan]")
        try:
            driver.navigate_to_perplexity()
            if debug:
                console.print("[green]✓ Navigation successful[/green]")
        except Exception as nav_error:
            console.print(f"[red]✗ Failed to navigate: {nav_error}[/red]")
            if debug:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            # Don't close browser immediately - let user see what happened
            if not headless:
                console.print("[yellow]Browser will remain open for 10 seconds for inspection...[/yellow]")
                time.sleep(10)
            raise
        
        if debug:
            console.print("[cyan]Performing search...[/cyan]")
        
        # Perform search programmatically with structured output
        try:
            # Adjust timeout based on mode: Research (5 min), Labs (16 min), Search (2 min)
            mode_timeouts = {
                'research': 300000,  # 5 minutes
                'labs': 960000,      # 16 minutes
                'search': 120000     # 2 minutes
            }
            search_timeout = mode_timeouts.get(mode.lower(), 120000)
            
            result = driver.search(
                query,
                mode=mode,
                wait_for_response=True, 
                timeout=search_timeout,
                extract_images=extract_images,
                image_dir=image_dir if extract_images else None,
                structured=True
            )
        except Exception as search_error:
            console.print(f"[red]✗ Search failed: {search_error}[/red]")
            if debug:
                import traceback
                console.print(f"[dim]{traceback.format_exc()}[/dim]")
            # Don't close browser immediately - let user see what happened
            if not headless:
                console.print("[yellow]Browser will remain open for 10 seconds for inspection...[/yellow]")
                time.sleep(10)
            raise
        
        if not result:
            console.print("[yellow]⚠ No response received[/yellow]")
            if not headless and not keep_browser_open:
                console.print("[yellow]Browser will remain open for 5 seconds...[/yellow]")
                time.sleep(5)
            return
        
        # Display or save result
        if output:
            from pathlib import Path
            import json
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            if isinstance(result, dict):
                with open(output, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2)
            else:
                with open(output, 'w', encoding='utf-8') as f:
                    f.write(result)
            console.print(f"\n[green]✓ Answer saved to: {output}[/green]")
        else:
            # Display structured output like API method with improved formatting
            if isinstance(result, dict):
                answer = result.get('answer', '').strip()
                
                # Clean up answer text - remove leading UI elements and query repetition
                if answer:
                    lines = answer.split('\n')
                    cleaned_lines = []
                    skip_ui_elements = ['account', 'upgrade', 'install', 'download comet', 'deep dive']
                    
                    for line in lines:
                        line_lower = line.lower().strip()
                        # Skip obvious UI elements
                        if any(ui in line_lower for ui in skip_ui_elements) and len(line_lower) < 30:
                            continue
                        # Skip if line is just "###" followed by query text
                        if line.startswith('###') and len(line) > 100:
                            continue
                        cleaned_lines.append(line)
                    
                    answer = '\n'.join(cleaned_lines).strip()
                
                console.print("\n[bold white on blue] ANSWER [/bold white on blue]")
                console.print()
                
                # Print answer with markdown rendering for better formatting
                if answer:
                    # Disable markdown parser debug logging
                    import logging
                    markdown_logger = logging.getLogger('markdown_it')
                    old_level = markdown_logger.level
                    markdown_logger.setLevel(logging.WARNING)
                    
                    from rich.markdown import Markdown
                    from rich.theme import Theme
                    import re
                    
                    # Extract all inline links from answer for reference section
                    inline_links = []
                    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
                    for match in re.finditer(link_pattern, answer):
                        link_text = match.group(1)
                        link_url = match.group(2)
                        if link_url.startswith('http'):
                            inline_links.append({'text': link_text, 'url': link_url})
                    
                    # OPTIMIZATION: Clean up markdown tables by removing inline links
                    # Tables with [text](url) look messy - replace with just text
                    def clean_table_cells(text):
                        """Remove markdown links from table cells for cleaner display"""
                        lines = text.split('\n')
                        cleaned_lines = []
                        in_table = False
                        
                        for line in lines:
                            # Detect table rows (contain | separators)
                            if '|' in line and not line.strip().startswith('```'):
                                in_table = True
                                # Replace [text](url) with just text in table rows
                                cleaned_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
                                cleaned_lines.append(cleaned_line)
                            else:
                                if in_table and line.strip() == '':
                                    in_table = False
                                cleaned_lines.append(line)
                        
                        return '\n'.join(cleaned_lines)
                    
                    answer = clean_table_cells(answer)
                    
                    # Custom theme for better colors
                    custom_theme = Theme({
                        "markdown.h1": "bold cyan",
                        "markdown.h2": "bold bright_cyan",
                        "markdown.h3": "bold yellow",
                        "markdown.h4": "bold bright_yellow",
                        "markdown.link": "dim bright_green",
                        "markdown.link_url": "dim green",
                        "markdown.code": "bright_magenta",
                        "markdown.code_block": "bright_magenta",
                        "markdown.item.bullet": "bright_cyan",
                        "markdown.item.number": "bright_cyan",
                        "markdown.block_quote": "dim italic",
                    })
                    
                    # Create console with custom theme
                    from rich.console import Console as RichConsole
                    themed_console = RichConsole(theme=custom_theme)
                    
                    md = Markdown(answer)
                    themed_console.print(md)
                    
                    # Restore logging level
                    markdown_logger.setLevel(old_level)
                else:
                    console.print("[yellow]No answer content extracted[/yellow]")
                
                console.print()
                
                # Combine inline links and sources for unified reference section
                all_references = []
                seen_urls = set()
                
                # Add inline links first (with deduplication)
                if 'inline_links' in locals() and inline_links:
                    for link in inline_links:
                        url = link['url']
                        if url not in seen_urls:
                            seen_urls.add(url)
                            all_references.append({
                                'title': link['text'],
                                'url': url,
                                'type': 'inline'
                            })
                
                # Add sources (with deduplication)
                if result.get('sources'):
                    for source in result['sources']:
                        url = source.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_references.append({
                                'title': source.get('title', 'N/A'),
                                'url': url,
                                'type': 'source'
                            })
                
                # Display all references
                if all_references:
                    console.print("\n[bold white on cyan] REFERENCES [/bold white on cyan]")
                    console.print()
                    for idx, ref in enumerate(all_references, 1):
                        title = ref['title']
                        url = ref['url']
                        
                        # Shorten very long URLs for display
                        display_url = url
                        if len(url) > 80:
                            # Keep domain + path start + ... + end
                            from urllib.parse import urlparse
                            try:
                                parsed = urlparse(url)
                                domain = parsed.netloc
                                path = parsed.path
                                if len(path) > 50:
                                    display_url = f"{parsed.scheme}://{domain}{path[:30]}...{path[-15:]}"
                            except:
                                display_url = url[:75] + "..."
                        
                        if url and url != title:
                            console.print(f"  [cyan]{idx}.[/cyan] [bold]{title}[/bold]")
                            console.print(f"      [link={url}][dim bright_green]{display_url}[/dim bright_green][/link]")
                        else:
                            console.print(f"  [cyan]{idx}.[/cyan] [bold]{title}[/bold]")
                    console.print()
                
                if result.get('related_questions'):
                    console.print("\n[bold white on yellow] RELATED QUESTIONS [/bold white on yellow]")
                    console.print()
                    for idx, q in enumerate(result['related_questions'], 1):
                        console.print(f"  [yellow]{idx}.[/yellow] [italic]{q}[/italic]")
                    console.print()
                
                # Show metadata with better formatting
                console.print()
                metadata_parts = []
                metadata_parts.append(f"[cyan]Answer:[/cyan] {len(result.get('answer', ''))} chars")
                metadata_parts.append(f"[cyan]References:[/cyan] {len(all_references)}")
                metadata_parts.append(f"[cyan]Mode:[/cyan] {result.get('mode', 'unknown')}")
                if result.get('model'):
                    metadata_parts.append(f"[cyan]Model:[/cyan] {result.get('model')}")
                console.print("[dim]" + " | ".join(metadata_parts) + "[/dim]")
            else:
                console.print("\n[bold green]Answer:[/bold green]")
                console.print(result)
                console.print(f"\n[dim]Response length: {len(result)} characters[/dim]")
        
        # Export as Markdown if requested
        if export_markdown:
            try:
                if debug:
                    console.print("\n[cyan]Exporting thread as Markdown...[/cyan]")
                
                export_path = driver.export_as_markdown(output_dir=export_dir)
                
                if export_path:
                    console.print(f"\n[green]✓ Thread exported as Markdown: {export_path}[/green]")
                else:
                    console.print("\n[yellow]⚠ Export completed but no file path returned[/yellow]")
            except Exception as export_error:
                console.print(f"\n[red]✗ Failed to export as Markdown: {export_error}[/red]")
                if debug:
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
                # Don't fail the entire command if export fails
                console.print("[yellow]Continuing...[/yellow]")
        
        # Keep browser open if requested
        if keep_browser_open:
            if not headless:
                console.print("\n[yellow]Browser will remain open - press Ctrl+C to close[/yellow]")
                try:
                    import time
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Closing browser...[/yellow]")
            else:
                console.print("\n[yellow]⚠ --keep-browser-open requires non-headless mode. Browser will close.[/yellow]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        if debug:
            import traceback
            console.print(f"\n[dim]Full traceback:[/dim]")
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
        # If browser was initialized, keep it open briefly for debugging (non-headless only)
        if driver_initialized and not headless and not keep_browser_open:
            console.print("\n[yellow]Browser will remain open for 15 seconds for inspection...[/yellow]")
            console.print("[yellow]Press Ctrl+C to close immediately[/yellow]")
            try:
                import time
                time.sleep(15)
            except KeyboardInterrupt:
                console.print("\n[yellow]Closing browser...[/yellow]")
    finally:
        if 'driver' in locals() and driver_initialized:
            if not keep_browser_open:
                try:
                    driver.close()
                    if debug:
                        console.print("[dim]Browser closed[/dim]")
                except Exception as close_error:
                    if debug:
                        console.print(f"[yellow]Warning: Error closing browser: {close_error}[/yellow]")


@cli.command('browser-batch')
@click.argument('queries', nargs=-1, required=True)
@click.option('--profile', '-p', help='Cookie profile to use')
@click.option('--headless', is_flag=True, help='Run in headless mode')
@click.option('--output', '-o', type=click.Path(), help='Save results to file')
@click.option('--user-data-dir', type=click.Path(), help='Persistent browser profile directory')
@click.option('--persistent', is_flag=True, help='Use persistent context')
@click.option('--max-concurrent', default=3, help='Maximum concurrent tabs (default: 3)')
@click.option('--extract-images', is_flag=True, help='Extract and save images from responses')
@click.option('--image-dir', type=click.Path(), default='_resources', help='Directory to save images (default: _resources)')
def browser_batch(queries, profile, headless, output, user_data_dir, persistent, max_concurrent, extract_images, image_dir):
    """
    Execute multiple queries in separate browser tabs concurrently
    
    Each query runs in its own Chrome tab for maximum speed and isolation.
    Results are extracted in structured format matching the API client.
    
    Examples:
        perplexity browser-batch "query 1" "query 2" "query 3"
        perplexity browser-batch "query 1" "query 2" "query 3" --output results.json
        perplexity browser-batch "query 1" "query 2" "query 3" --persistent --max-concurrent 5
    """
    if not queries:
        console.print("[red]No queries provided[/red]")
        return
    
    queries_list = list(queries)
    console.print(f"\n[bold cyan]Browser Batch Search[/bold cyan]")
    console.print(f"Processing {len(queries_list)} queries in separate tabs...\n")
    
    # Handle persistent context
    if persistent and not user_data_dir:
        from pathlib import Path
        profile_name = profile or "default"
        user_data_dir = f"browser_data/{profile_name}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Using persistent context: {user_data_dir}[/green]")
    
    # Load cookies if profile specified, or try default profile
    cookies = None
    cookie_manager = CookieManager()
    if profile and not persistent:
        cookies = cookie_manager.load_cookies(profile)
        if cookies:
            console.print(f"[green]✓ Loaded profile: {profile}[/green]")
    elif not persistent:
        # Try to load default profile if no profile specified
        try:
            cookies = cookie_manager.load_cookies("default")
            if cookies:
                console.print(f"[green]✓ Loaded default cookie profile[/green]")
        except:
            pass
    
    driver = PerplexityWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    # Set cookies BEFORE starting browser (will be injected into context before navigation)
    if cookies and not persistent:
        driver.set_cookies(cookies)
        console.print(f"[green]✓ Cookies loaded (will be injected before navigation)[/green]")
    
    try:
        console.print("[cyan]Starting browser...[/cyan]")
        driver.start()
        
        # Cookies are already injected in start() via _inject_cookies_into_context()
        driver.navigate_to_perplexity()
        
        console.print(f"[cyan]Executing {len(queries_list)} queries with max {max_concurrent} concurrent tabs...[/cyan]\n")
        
        # Execute batch search
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing queries...", total=len(queries_list))
            
            # Batch search removed - focus on single query for now
            # Execute queries one by one
            results = []
            for query in queries_list:
                try:
                    result = driver.search(
                        query=query,
                        wait_for_response=True,
                        timeout=120000,
                        extract_images=extract_images,
                        image_dir=image_dir if extract_images else None,
                        structured=True
                    )
                    results.append(result)
                except Exception as e:
                    results.append({
                        'query': query,
                        'answer': f'Error: {str(e)}',
                        'sources': [],
                        'related_questions': [],
                        'error': str(e)
                    })
            
            progress.update(task, completed=len(queries_list))
        
        # Display results
        console.print("\n[bold green]Results:[/bold green]\n")
        for idx, (query, result) in enumerate(zip(queries_list, results), 1):
            console.print(f"[bold cyan]Query {idx}: {query}[/bold cyan]")
            
            if isinstance(result, dict):
                if result.get('error'):
                    console.print(f"[red]Error: {result['error']}[/red]")
                else:
                    console.print(f"[green]Answer:[/green] {result.get('answer', '')[:150]}...")
                    if result.get('sources'):
                        console.print(f"[dim]Sources: {len(result['sources'])}[/dim]")
                    if result.get('related_questions'):
                        console.print(f"[dim]Related Questions: {len(result['related_questions'])}[/dim]")
            else:
                console.print(f"[green]Answer:[/green] {str(result)[:150]}...")
            console.print()
        
        # Save if requested
        if output:
            from pathlib import Path
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, 'w', encoding='utf-8') as f:
                json.dump([r if isinstance(r, dict) else {'query': q, 'answer': str(r)} for q, r in zip(queries_list, results)], f, indent=2)
            console.print(f"[green]✓ Results saved to: {output}[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise
    finally:
        if 'driver' in locals():
            driver.close()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def _get_platform_info():
    """
    Detect the current platform and return script information.
    Returns a dict with:
    - platform_type: 'windows', 'wsl2', 'linux', 'unknown'
    - script_name: The script to use (e.g., 'perplexity.ps1', 'perplexity.sh')
    - script_prefix: How to invoke it (e.g., '.\\', './')
    - is_windows: Boolean
    - is_wsl2: Boolean
    """
    import platform
    import os
    
    system = platform.system()
    is_windows = system == 'Windows'
    is_linux = system == 'Linux'
    is_wsl2 = False
    
    # Detect WSL2 specifically
    if is_linux:
        try:
            with open('/proc/version', 'r') as f:
                version_info = f.read().lower()
                is_wsl2 = 'microsoft' in version_info and 'wsl' in version_info
        except:
            pass
    
    # Determine script name and prefix
    if is_windows:
        script_name = 'perplexity.ps1'
        script_prefix = '.\\'
        platform_type = 'windows'
    elif is_wsl2:
        script_name = 'perplexity.sh'
        script_prefix = './'
        platform_type = 'wsl2'
    elif is_linux:
        script_name = 'perplexity.sh'
        script_prefix = './'
        platform_type = 'linux'
    else:
        # Fallback for other platforms
        script_name = 'perplexity.sh'
        script_prefix = './'
        platform_type = 'unknown'
    
    return {
        'platform_type': platform_type,
        'script_name': script_name,
        'script_prefix': script_prefix,
        'is_windows': is_windows,
        'is_wsl2': is_wsl2,
        'is_linux': is_linux
    }


def _format_command(platform_info, command, args=''):
    """
    Format a command with the appropriate script prefix and name.
    
    Args:
        platform_info: Result from _get_platform_info()
        command: The command (e.g., 'search', 'browser')
        args: Additional arguments (e.g., '--headless', query string)
    
    Returns:
        Formatted command string
    """
    script_cmd = f"{platform_info['script_prefix']}{platform_info['script_name']} {command}"
    if args:
        script_cmd += f" {args}"
    return script_cmd


def _print_login_instructions(platform_info, query, context='search'):
    """
    Print platform-specific login instructions.
    
    Args:
        platform_info: Result from _get_platform_info()
        query: The search query (for command examples)
        context: Context for the instructions ('search' or 'browser')
    """
    console.print("\n[cyan]To fix this:[/cyan]")
    
    if context == 'search':
        cmd1 = _format_command(platform_info, 'search', f'"{query}"')
        cmd2 = _format_command(platform_info, 'browser', '--persistent')
        console.print("[cyan]  1. Login without --headless (recommended):[/cyan]")
        console.print(f"[cyan]     {cmd1}[/cyan]")
        console.print("[cyan]  2. Or login separately first:[/cyan]")
        console.print(f"[cyan]     {cmd2}[/cyan]")
        console.print("[cyan]     (Login, then close browser and run search with --headless)[/cyan]\n")
    elif context == 'browser':
        cmd = _format_command(platform_info, 'browser', '--persistent')
        console.print("[cyan]  1. Run without --headless to login interactively:[/cyan]")
        console.print(f"[cyan]     {cmd}[/cyan]")
        console.print("[cyan]  2. Or login separately first:[/cyan]")
        console.print(f"[cyan]     {cmd}[/cyan]")
        console.print("[cyan]     (Then close browser and run search with --headless)[/cyan]\n")


def _smart_browser_search(query, search_mode_str, mode, model, sources, stream, output, format, profile, verbose, headless=False, keep_browser_open=False):
    """
    Smart browser search with automatic login handling
    - Checks for persistent browser session
    - If not logged in, opens browser for login (unless headless)
    - Performs search seamlessly
    - Supports headless mode and keeping browser open
    """
    from pathlib import Path
    import time
    
    # Determine profile name
    profile_name = profile or "default"
    user_data_dir = f"browser_data/{profile_name}"
    Path(user_data_dir).mkdir(parents=True, exist_ok=True)
    
    # Check if persistent session exists
    session_exists = Path(user_data_dir).exists() and any(Path(user_data_dir).iterdir())
    
    # In headless mode, we can't show browser for login, so skip login check
    # In non-headless mode, show browser for login if needed
    browser_headless = headless
    
    # If keep_browser_open is True, force non-headless so user can see browser
    if keep_browser_open:
        browser_headless = False
    
    # In headless mode, check if we have a persistent session first
    if browser_headless and not session_exists:
        platform_info = _get_platform_info()
        
        console.print("\n[yellow]⚠ No persistent session found and running in headless mode[/yellow]")
        console.print("[yellow]⚠ Headless mode cannot handle login interactively[/yellow]")
        _print_login_instructions(platform_info, query, context='browser')
        return
    
    driver = PerplexityWebDriver(
        headless=browser_headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    try:
        if verbose:
            console.print("[cyan]Starting browser...[/cyan]")
        driver.start(debug_network=verbose)
        
        # Navigate to Perplexity and wait for page to be ready
        driver.navigate_to_perplexity()
        
        # Ensure we're on the right page - minimal wait
        import time
        time.sleep(0.5)  # Brief wait for page to settle
        
        # Verify we're on Perplexity homepage
        try:
            current_url = driver.page.url
            if 'perplexity.ai' not in current_url.lower():
                if verbose:
                    console.print(f"[dim]Redirected to: {current_url}, navigating to Perplexity...[/dim]")
                driver.navigate_to_perplexity()
                time.sleep(0.5)
        except:
            pass
        
        # Check if already logged in by looking for search box and checking page content
        # If persistent session exists, be more lenient with login detection
        is_logged_in = False
        
        # If we have a persistent session, assume logged in initially (will verify by trying to search)
        if session_exists:
            is_logged_in = True
            if verbose:
                console.print("[dim]Persistent session found - assuming logged in[/dim]")
        
        # Try to verify login status, but don't fail if we have a session
        try:
            # Brief wait for page to load
            time.sleep(0.5)  # Reduced wait time
            # Use JavaScript to check login status more reliably
            login_status = driver.page.evaluate("""
                () => {
                    // Check for search box (logged in users see this)
                    const searchBox = document.querySelector('[contenteditable="true"], textarea');
                    if (!searchBox) return false;
                    
                    // Check for login/sign in buttons/links (more lenient - only check prominent ones)
                    const loginLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                        const href = (a.getAttribute('href') || '').toLowerCase();
                        const text = (a.textContent || '').toLowerCase();
                        // Only count prominent login links (in header/nav, not footer)
                        const parent = a.closest('header, nav, [class*="header"], [class*="nav"]');
                        if (parent && (href.includes('login') || href.includes('sign') || 
                               text.includes('sign in') || text.includes('log in'))) {
                            return true;
                        }
                        return false;
                    });
                    
                    // Check for sign in buttons (only prominent ones)
                    const buttons = Array.from(document.querySelectorAll('button')).filter(btn => {
                        const text = (btn.textContent || '').toLowerCase();
                        const parent = btn.closest('header, nav, [class*="header"], [class*="nav"]');
                        if (parent && (text.includes('sign in') || text.includes('log in'))) {
                            return true;
                        }
                        return false;
                    });
                    
                    // If we have search box and no prominent login elements, we're logged in
                    return searchBox && loginLinks.length === 0 && buttons.length === 0;
                }
            """)
            # Update login status if we got a clear result
            if login_status:
                is_logged_in = True
            elif not session_exists:
                # Only set to false if we don't have a session
                is_logged_in = False
            # If session exists but detection failed, keep is_logged_in = True (assume logged in)
        except Exception as e:
            # If we have a session, assume logged in even if detection fails
            if session_exists:
                if verbose:
                    console.print(f"[dim]Login check failed but session exists, assuming logged in: {e}[/dim]")
                is_logged_in = True
            else:
                if verbose:
                    console.print(f"[dim]Login check failed: {e}[/dim]")
                pass
        
        # If not logged in, wait for user to login (only if not headless)
        if not is_logged_in:
            if browser_headless:
                platform_info = _get_platform_info()
                
                console.print("\n[yellow]⚠ Not logged in and running in headless mode[/yellow]")
                console.print("[yellow]⚠ Headless mode cannot handle login interactively[/yellow]")
                _print_login_instructions(platform_info, query, context='browser')
                driver.close()
                return
            else:
                console.print("\n[yellow]⚠ Not logged in - please log in to Perplexity in the browser window[/yellow]")
                console.print("[cyan]Waiting for login...[/cyan]")
                console.print("[dim]The browser will automatically proceed once you're logged in[/dim]\n")
                
                # Wait for login - check periodically if login elements disappear
                max_wait = 300  # 5 minutes max
                wait_interval = 2  # Check every 2 seconds
                waited = 0
                
                while waited < max_wait:
                    try:
                        time.sleep(wait_interval)
                        waited += wait_interval
                        
                        # Check if logged in now using JavaScript
                        try:
                            login_status = driver.page.evaluate("""
                                () => {
                                    const searchBox = document.querySelector('[contenteditable="true"], textarea');
                                    if (!searchBox) return false;
                                    
                                    const loginLinks = Array.from(document.querySelectorAll('a')).filter(a => {
                                        const href = (a.getAttribute('href') || '').toLowerCase();
                                        const text = (a.textContent || '').toLowerCase();
                                        return href.includes('login') || href.includes('sign') || 
                                               text.includes('sign in') || text.includes('log in');
                                    });
                                    
                                    const buttons = Array.from(document.querySelectorAll('button')).filter(btn => {
                                        const text = (btn.textContent || '').toLowerCase();
                                        return text.includes('sign in') || text.includes('log in');
                                    });
                                    
                                    return searchBox && loginLinks.length === 0 && buttons.length === 0;
                                }
                            """)
                            if login_status:
                                is_logged_in = True
                                break
                        except:
                            pass
                        
                        # Refresh page periodically to check status
                        if waited % 10 == 0:
                            driver.page.reload(wait_until="domcontentloaded")
                            time.sleep(1)
                            
                    except KeyboardInterrupt:
                        console.print("\n[yellow]Interrupted by user[/yellow]")
                        return
                    except:
                        continue
                
                if not is_logged_in:
                    console.print("\n[yellow]⚠ Login timeout - proceeding anyway (you may need to login manually)[/yellow]")
        
        if is_logged_in:
            if verbose:
                console.print("[green]✓ Logged in - performing search...[/green]\n")
        else:
            # In non-headless mode, if still not logged in after waiting, try to proceed
            # The search function will handle the error if it can't find search box
            console.print("[yellow]⚠ Proceeding with search (may fail if not logged in)...[/yellow]\n")
        
        # Perform search - if we have a session, try it even if login detection was uncertain
        try:
            # Before searching, ensure we're on the right page
            try:
                current_url = driver.page.url
                if 'perplexity.ai' not in current_url.lower():
                    if verbose:
                        console.print(f"[dim]Not on Perplexity, navigating... (current: {current_url})[/dim]")
                    driver.navigate_to_perplexity()
                    time.sleep(0.5)
            except:
                pass
            
            if verbose:
                console.print(f"\n[cyan]Searching: {query}[/cyan]")
                console.print("[dim]This may take 30-60 seconds...[/dim]\n")
            else:
                # Minimal output - just show we're working
                console.print(f"\n[dim]Searching...[/dim]")
            
            response_text = driver.search(
                query,
                wait_for_response=True,
                timeout=120000
            )
            
            if not response_text:
                console.print("[yellow]⚠ No response received from search[/yellow]")
                return
            
            console.print("[green]✓ Search completed[/green]\n")
        except Exception as search_error:
            error_msg = str(search_error)
            if "Could not find search input" in error_msg or "not logged in" in error_msg.lower():
                # Check if this is a session issue - maybe session expired
                if session_exists:
                    console.print("\n[yellow]⚠ Search failed - session may have expired or page didn't load correctly[/yellow]")
                    console.print("[yellow]⚠ The persistent session exists but the search box wasn't found[/yellow]")
                    
                    # Try to get more info about what went wrong
                    try:
                        page_url = driver.page.url
                        page_title = driver.page.title()
                        console.print(f"[dim]Page was at: {page_url}[/dim]")
                        console.print(f"[dim]Page title: {page_title}[/dim]")
                        
                        # Check if we're on a login page
                        if 'login' in page_url.lower() or 'sign' in page_url.lower():
                            console.print("[yellow]⚠ Detected login page - session expired, please login again[/yellow]")
                    except:
                        pass
                else:
                    if browser_headless:
                        console.print("\n[red]✗ Search failed - likely not logged in[/red]")
                        console.print("[yellow]⚠ In headless mode, you must login first[/yellow]")
                
                # Get platform info and print login instructions
                platform_info = _get_platform_info()
                _print_login_instructions(platform_info, query, context='search')
                raise
            else:
                raise
        
        if not response_text:
            console.print("[yellow]⚠ No response received[/yellow]")
            return
        
        # Display or save result
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, 'w', encoding='utf-8') as f:
                f.write(response_text)
            console.print(f"\n[green]✓ Answer saved to: {output}[/green]")
        else:
            console.print("\n[bold green]Answer:[/bold green]")
            console.print(response_text)
        
        # Keep browser open if requested
        if keep_browser_open:
            console.print("\n[yellow]Browser will remain open - press Ctrl+C to close[/yellow]")
            try:
                driver.interactive_mode()
            except KeyboardInterrupt:
                console.print("\n[yellow]Closing browser...[/yellow]")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        raise
    finally:
        if not keep_browser_open:
            driver.close()
        else:
            # Browser will be closed when user presses Ctrl+C in interactive_mode
            pass


def _fallback_to_browser_search(query, profile, output, format, headless, verbose):
    """Fallback to browser automation when API fails"""
    from pathlib import Path
    
    console.print("[cyan]Starting browser automation...[/cyan]")
    
    # Handle persistent context
    user_data_dir = None
    if profile:
        user_data_dir = f"browser_data/{profile}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
    
    # Load cookies if profile specified
    cookies = None
    if profile:
        connection_manager = ConnectionManager(verbose=verbose)
        client_test = connection_manager.setup_connection(profile=profile, skip_web_automation=True)
        if client_test:
            cookies = client_test.get_cookies()
    
    driver = PerplexityWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    # Set cookies BEFORE starting browser (will be injected into context before navigation)
    if cookies:
        driver.set_cookies(cookies)
    
    try:
        driver.start(debug_network=verbose)
        # Cookies are already injected in start() via _inject_cookies_into_context()
        driver.navigate_to_perplexity()
        
        # Perform search
        response_text = driver.search(
            query,
            wait_for_response=True,
            timeout=120000
        )
        
        if not response_text:
            console.print("[yellow]⚠ No response received[/yellow]")
            return
        
        # Display or save result
        if output:
            Path(output).parent.mkdir(parents=True, exist_ok=True)
            with open(output, 'w', encoding='utf-8') as f:
                f.write(response_text)
            console.print(f"\n[green]✓ Answer saved to: {output}[/green]")
        else:
            console.print("\n[bold green]Answer:[/bold green]")
            console.print(response_text)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Browser automation error: {e}[/red]")
        raise
    finally:
        driver.close()


def _display_response(response, format):
    """Display search response in specified format - matches browser automation styling"""
    if format == 'json':
        console.print_json(json.dumps(response.to_dict(), indent=2))
    
    elif format == 'markdown':
        md = Markdown(response.to_markdown())
        console.print(md)
    
    else:  # text - use same beautiful formatting as browser automation
        answer = response.answer if response.answer else ""
        
        # Extract answer from raw_response if not in response.answer
        if not answer and hasattr(response, 'raw_response'):
            raw = response.raw_response
            if isinstance(raw, dict) and '_all_chunks' in raw:
                all_chunks = raw['_all_chunks']
                for chunk in reversed(all_chunks):
                    if isinstance(chunk, dict) and chunk.get('step_type') == 'FINAL':
                        content = chunk.get('content', {})
                        if isinstance(content, dict) and 'answer' in content:
                            answer_str = content['answer']
                            try:
                                answer_obj = json.loads(answer_str) if isinstance(answer_str, str) else answer_str
                                if isinstance(answer_obj, dict) and 'answer' in answer_obj:
                                    answer = answer_obj['answer']
                                    break
                            except:
                                answer = answer_str
                                break
                # If no FINAL step, try chunks
                if not answer:
                    for chunk in reversed(all_chunks):
                        if isinstance(chunk, dict):
                            content = chunk.get('content', {})
                            if isinstance(content, dict) and 'chunks' in content:
                                chunks = content['chunks']
                                if isinstance(chunks, list):
                                    answer = ''.join([c for c in chunks if isinstance(c, str)])
                                    if answer:
                                        break
        
        answer = answer.strip()
        
        # Clean up answer text - remove leading UI elements
        if answer:
            lines = answer.split('\n')
            cleaned_lines = []
            skip_ui_elements = ['account', 'upgrade', 'install', 'download comet', 'deep dive']
            
            for line in lines:
                line_lower = line.lower().strip()
                # Skip obvious UI elements
                if any(ui in line_lower for ui in skip_ui_elements) and len(line_lower) < 30:
                    continue
                # Skip if line is just "###" followed by long query text
                if line.startswith('###') and len(line) > 100:
                    continue
                cleaned_lines.append(line)
            
            answer = '\n'.join(cleaned_lines).strip()
        
        console.print("\n[bold white on blue] ANSWER [/bold white on blue]")
        console.print()
        
        # Print answer with markdown rendering for better formatting
        if answer:
            # Disable markdown parser debug logging
            import logging
            markdown_logger = logging.getLogger('markdown_it')
            old_level = markdown_logger.level
            markdown_logger.setLevel(logging.WARNING)
            
            from rich.markdown import Markdown
            from rich.theme import Theme
            import re
            
            # Extract all inline links from answer for reference section
            inline_links = []
            link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
            for match in re.finditer(link_pattern, answer):
                link_text = match.group(1)
                link_url = match.group(2)
                if link_url.startswith('http'):
                    inline_links.append({'text': link_text, 'url': link_url})
            
            # OPTIMIZATION: Clean up markdown tables by removing inline links
            # Tables with [text](url) look messy - replace with just text
            def clean_table_cells(text):
                """Remove markdown links from table cells for cleaner display"""
                lines = text.split('\n')
                cleaned_lines = []
                in_table = False
                
                for line in lines:
                    # Detect table rows (contain | separators)
                    if '|' in line and not line.strip().startswith('```'):
                        in_table = True
                        # Replace [text](url) with just text in table rows
                        cleaned_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
                        cleaned_lines.append(cleaned_line)
                    else:
                        if in_table and line.strip() == '':
                            in_table = False
                        cleaned_lines.append(line)
                
                return '\n'.join(cleaned_lines)
            
            answer = clean_table_cells(answer)
            
            # Custom theme for better colors (same as browser automation)
            custom_theme = Theme({
                "markdown.h1": "bold cyan",
                "markdown.h2": "bold bright_cyan",
                "markdown.h3": "bold yellow",
                "markdown.h4": "bold bright_yellow",
                "markdown.link": "dim bright_green",
                "markdown.link_url": "dim green",
                "markdown.code": "bright_magenta",
                "markdown.code_block": "bright_magenta",
                "markdown.item.bullet": "bright_cyan",
                "markdown.item.number": "bright_cyan",
                "markdown.block_quote": "dim italic",
            })
            
            # Create console with custom theme
            from rich.console import Console as RichConsole
            themed_console = RichConsole(theme=custom_theme)
            
            md = Markdown(answer)
            themed_console.print(md)
            
            # Restore logging level
            markdown_logger.setLevel(old_level)
        else:
            console.print("[yellow]No answer content extracted[/yellow]")
        
        console.print()
        
        # Combine inline links and sources for unified reference section (same as browser automation)
        all_references = []
        seen_urls = set()
        
        # Add inline links first (with deduplication)
        if inline_links:
            for link in inline_links:
                url = link['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_references.append({
                        'title': link['text'],
                        'url': url,
                        'type': 'inline'
                    })
        
        # Add sources (with deduplication)
        # Handle both dict format and SearchResponse.Source objects
        if response.sources:
            for source in response.sources:
                # Handle both dict and object formats
                if isinstance(source, dict):
                    url = source.get('url', '')
                    title = source.get('title', 'N/A')
                else:
                    # It's a Source object
                    url = getattr(source, 'url', '')
                    title = getattr(source, 'title', 'N/A')
                
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_references.append({
                        'title': title,
                        'url': url,
                        'type': 'source'
                    })
        
        # Display all references
        if all_references:
            console.print("\n[bold white on cyan] REFERENCES [/bold white on cyan]")
            console.print()
            for idx, ref in enumerate(all_references, 1):
                title = ref['title']
                url = ref['url']
                
                # Shorten very long URLs for display
                display_url = url
                if len(url) > 80:
                    # Keep domain + path start + ... + end
                    from urllib.parse import urlparse
                    try:
                        parsed = urlparse(url)
                        domain = parsed.netloc
                        path = parsed.path
                        if len(path) > 50:
                            display_url = f"{parsed.scheme}://{domain}{path[:30]}...{path[-15:]}"
                    except:
                        display_url = url[:75] + "..."
                
                if url and url != title:
                    console.print(f"  [cyan]{idx}.[/cyan] [bold]{title}[/bold]")
                    console.print(f"      [link={url}][dim bright_green]{display_url}[/dim bright_green][/link]")
                else:
                    console.print(f"  [cyan]{idx}.[/cyan] [bold]{title}[/bold]")
            console.print()
        
        if response.related_questions:
            console.print("\n[bold white on yellow] RELATED QUESTIONS [/bold white on yellow]")
            console.print()
            for idx, q in enumerate(response.related_questions, 1):
                console.print(f"  [yellow]{idx}.[/yellow] [italic]{q}[/italic]")
            console.print()
        
        # Show metadata with better formatting
        console.print()
        metadata_parts = []
        metadata_parts.append(f"[cyan]Answer:[/cyan] {len(answer)} chars")
        metadata_parts.append(f"[cyan]References:[/cyan] {len(all_references)}")
        if hasattr(response, 'mode') and response.mode:
            metadata_parts.append(f"[cyan]Mode:[/cyan] {response.mode}")
        if hasattr(response, 'model') and response.model:
            metadata_parts.append(f"[cyan]Model:[/cyan] {response.model}")
        console.print("[dim]" + " | ".join(metadata_parts) + "[/dim]")


def _display_labs_response(response, format):
    """Display Labs project response"""
    if format == 'json':
        console.print_json(json.dumps(response.to_dict(), indent=2))
    
    elif format == 'markdown':
        md = Markdown(response.to_markdown())
        console.print(md)
    
    else:  # text
        console.print(f"\n[bold green]Labs Project Created:[/bold green]")
        console.print(response.answer)
        
        if hasattr(response, 'project_id') and response.project_id:
            console.print(f"\n[bold cyan]Project ID:[/bold cyan] {response.project_id}")
        
        if response.sources:
            console.print(f"\n[bold cyan]Resources ({len(response.sources)}):[/bold cyan]")
            for idx, source in enumerate(response.sources[:5], 1):
                console.print(f"  {idx}. {source.get('title', 'N/A')}")


def _save_output(response, filepath, format):
    """Save response to file"""
    filepath = Path(filepath)
    
    if format == 'json':
        with open(filepath, 'w') as f:
            json.dump(response.to_dict(), f, indent=2)
    
    elif format == 'markdown':
        with open(filepath, 'w') as f:
            f.write(response.to_markdown())
    
    else:  # text
        with open(filepath, 'w') as f:
            f.write(f"Query: {response.query}\n\n")
            f.write(f"Answer:\n{response.answer}\n\n")
            if response.sources:
                f.write("Sources:\n")
                for idx, source in enumerate(response.sources, 1):
                    f.write(f"{idx}. {source.get('title')}\n")
                    f.write(f"   {source.get('url')}\n")


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()