"""
Grok Chat API Wrapper - CLI Interface
"""
import sys
import os
from pathlib import Path

# Setup imports
cli_file = Path(__file__).resolve()
if 'src' in str(cli_file.parent):
    project_root = cli_file.parent.parent.parent
    if project_root.exists() and (project_root / 'src').exists():
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

import click
import json
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Configure logging to show INFO level messages with emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[logging.StreamHandler()]
)

# Fix encoding issues for all platforms
# Force UTF-8 encoding for consistent output across Windows, Linux, and WSL2
# This ensures emojis and special characters display correctly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
else:
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ensure emoji support
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import core modules
try:
    from src.core.client import GrokClient
    from src.core.models import GrokException, AuthenticationError, NetworkError, APIError
    from src.core.model_mapping import get_model_params, get_model_display_name
    from src.automation.web_driver import GrokWebDriver
    from src.automation.cookie_manager import CookieManager
except ImportError:
    from core.client import GrokClient
    from core.models import GrokException, AuthenticationError, NetworkError
    from core.model_mapping import get_model_params, get_model_display_name
    from automation.web_driver import GrokWebDriver
    from automation.cookie_manager import CookieManager

# Create console with UTF-8 support and emoji enabled
console = Console(
    force_terminal=True,
    color_system="auto",
    width=None,  # Auto-detect terminal width
    legacy_windows=False  # Use modern Windows terminal features
)


def _setup_client_with_automation(profile=None, verbose=False, headless=False, persistent=False):
    """
    Setup client with automatic browser-based authentication
    
    Returns:
        tuple: (client, use_browser_automation)
    """
    cookie_manager = CookieManager()
    cookies = None
    
    # Try to load cookies from profile (or default)
    profile_name = profile or "default"
    cookies = cookie_manager.load_cookies(profile_name)
    if cookies and verbose:
        console.print(f"[green]✓ Loaded cookie profile: {profile_name}[/green]")
    
    # Try auto-extracting from browser if no saved cookies
    if not cookies:
        if verbose:
            console.print("[cyan]No saved cookies found, trying to extract from browser...[/cyan]")
        try:
            cookies = cookie_manager.auto_extract(browser='chrome')
            if cookies:
                # Save to default profile
                cookie_manager.save_cookies(cookies, "default")
                if verbose:
                    console.print(f"[green]✓ Extracted and saved {len(cookies)} cookies from Chrome[/green]")
        except Exception as e:
            if verbose:
                console.print(f"[yellow]Browser extraction failed: {e}[/yellow]")
    
    # If we have cookies, try to use API client
    if cookies:
        try:
            client = GrokClient(cookies=cookies)
            # Test with a simple request (we'll handle errors in the actual chat call)
            return client, False
        except Exception as e:
            if verbose:
                console.print(f"[yellow]Cookie-based client failed: {e}, will use browser automation[/yellow]")
    
    # Fall back to browser automation
    return None, True


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    Grok Chat API Wrapper
    
    A terminal interface for Grok chat with automatic authentication.
    
    Examples:
        grok "Hello, how are you?"
        grok "Explain quantum computing" --stream
        grok "Write a Python function" --model grok-4 --output response.txt
    """
    pass


@cli.command()
@click.argument('message', nargs=-1, required=True)
@click.option('--model', '-m', default='auto', 
              help='Model to use: auto, fast, expert, grok-4-fast, heavy, grok-4, grok-2, grok-4.1, grok-4.1-think (default: auto)')
@click.option('--stream', '-s', is_flag=True, help='Stream response in real-time')
@click.option('--output', '-o', type=click.Path(), help='Save response to file')
@click.option('--format', '-f', type=click.Choice(['text', 'json', 'markdown']), 
              default='text', help='Output format')
@click.option('--profile', '-p', help='Cookie profile to use')
@click.option('--headless', is_flag=True, help='Run browser in headless mode')
@click.option('--persistent', is_flag=True, help='Use persistent browser session')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
@click.option('--debug', '--DebugMode', is_flag=True, help='Show debug logs and timing information')
@click.option('--DeepSearch', '--deep-search', is_flag=True, help='Enable DeepSearch mode for enhanced research')
@click.option('--private', is_flag=True, help='Enable Private chat mode')
@click.option('--keep-browser-open', is_flag=True, help='Keep browser open after chat')
def chat(message, model, stream, output, format, profile, headless, persistent, verbose, keep_browser_open, debug, deepsearch, private):
    """
    Send a message to Grok chat
    
    Examples:
        grok chat "Hello!"
        grok chat "Explain AI" --stream
        grok chat "Write code" --model grok-4 --output response.txt
        grok chat "Research topic" --DeepSearch
    """
    message = ' '.join(message) if isinstance(message, tuple) else message
    
    # Get model parameters
    model_name, model_mode = get_model_params(model)
    model_display = get_model_display_name(model)
    
    if verbose:
        console.print(f"\n[bold cyan]Grok Chat[/bold cyan]")
        console.print(f"Message: {message}")
        console.print(f"Model: {model_display} ({model_name}, {model_mode})")
        console.print(f"Stream: {stream}\n")
    
    # Set debug mode for logging
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('src.automation').setLevel(logging.DEBUG)
    else:
        # Only show warnings and errors by default
        logging.getLogger().setLevel(logging.WARNING)
        logging.getLogger('src.automation').setLevel(logging.WARNING)
    
    # Try to setup client with cookies first
    client, use_browser = _setup_client_with_automation(
        profile=profile,
        verbose=verbose,
        headless=headless,
        persistent=persistent
    )
    
    # Use browser automation if needed
    if use_browser or not client:
        _browser_chat(
            message=message,
            model=model,
            model_name=model_name,
            model_mode=model_mode,
            stream=stream,
            output=output,
            format=format,
            profile=profile,
            headless=headless,
            persistent=persistent,
            verbose=verbose,
            debug=debug,
            deepsearch=deepsearch,
            private=private,
            keep_browser_open=keep_browser_open
        )
        return
    
    # Use API client
    try:
        if stream:
            _stream_chat(client, message, model_name, model_mode, output, format, verbose)
        else:
            _complete_chat(client, message, model_name, model_mode, output, format, verbose)
    except (AuthenticationError, APIError) as e:
        # Check if it's a 403 (Cloudflare block) or auth error
        is_cloudflare = isinstance(e, APIError) and hasattr(e, 'status_code') and e.status_code == 403
        is_auth_error = isinstance(e, AuthenticationError) or (isinstance(e, APIError) and hasattr(e, 'status_code') and e.status_code in [401, 403])
        
        if is_cloudflare or is_auth_error:
            if debug:
                console.print("\n[yellow]⚠ API blocked or cookies expired - switching to browser automation...[/yellow]")
            
            # Fall back to browser automation (cookie extraction already handled in _browser_chat)
            _browser_chat(
                message=message,
                model=model,
                model_name=model_name,
                model_mode=model_mode,
                stream=stream,
                output=output,
                format=format,
                profile=profile,
                headless=headless,
                persistent=persistent,
                verbose=verbose,
                debug=debug,
                deepsearch=deepsearch,
                private=private,
                keep_browser_open=keep_browser_open
            )
        else:
            raise
    except (NetworkError, GrokException) as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        if verbose:
            console.print("\n[yellow]💡 Tip: Try using browser automation with --headless flag[/yellow]")
        raise


def _stream_chat(client, message, model_name, model_mode, output, format, verbose):
    """Handle streaming chat response"""
    console.print("\n[bold cyan]Grok Response (streaming):[/bold cyan]\n")
    
    full_message = ""
    output_file = None
    
    if output:
        output_file = open(output, 'w', encoding='utf-8')
    
    try:
        for token in client.chat(message, model_name=model_name, model_mode=model_mode, stream=True):
            if token.token:
                console.print(token.token, end='', style='white')
                full_message += token.token
                if output_file:
                    output_file.write(token.token)
                    output_file.flush()
        
        console.print("\n")
        
        if output_file:
            output_file.close()
            console.print(f"\n[green]✓ Response saved to: {output}[/green]")
    except Exception:
        if output_file:
            output_file.close()
        raise


def _complete_chat(client, message, model_name, model_mode, output, format, verbose):
    """Handle complete (non-streaming) chat response"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Chatting with Grok...", total=None)
        
        response = client.chat(message, model_name=model_name, model_mode=model_mode, stream=False)
        
        progress.update(task, completed=True)
    
    # Display response
    _display_response(response, format)
    
    # Save to file if specified
    if output:
        _save_output(response, output, format)
        console.print(f"\n[green]✓ Saved to: {output}[/green]")


def _browser_chat(message, model, model_name, model_mode, stream, output, format, profile, headless, persistent, verbose, debug, deepsearch, private, keep_browser_open):
    """Use browser automation for chat with automatic cookie refresh"""
    from pathlib import Path
    
    # Setup persistent browser profile
    user_data_dir = None
    if persistent:
        profile_name = profile or "default"
        user_data_dir = f"browser_data/{profile_name}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        if verbose:
            console.print(f"[green]✓ Using persistent session: {user_data_dir}[/green]")
    
    # Load cookies if profile specified
    cookies = None
    cookie_manager = CookieManager()
    profile_name = profile or "default"
    
    if profile:
        cookies = cookie_manager.load_cookies(profile)
        if cookies and verbose:
            console.print(f"[green]✓ Loaded {len(cookies)} cookies from profile: {profile}[/green]")
    elif not persistent:
        # Try default profile
        cookies = cookie_manager.load_cookies("default")
        if cookies and verbose:
            console.print(f"[green]✓ Loaded {len(cookies)} cookies from default profile[/green]")
    
    # Try auto-extracting from browser if no cookies - try Firefox first (more reliable)
    if not cookies:
        if verbose:
            console.print("[cyan]No saved cookies, trying to extract from browser...[/cyan]")
        try:
            # Try Firefox first (more reliable on Windows)
            cookies = cookie_manager.auto_extract(browser='firefox')
            if cookies:
                cookie_manager.save_cookies(cookies, profile_name)
                if verbose:
                    console.print(f"[green]✓ Extracted and saved {len(cookies)} cookies from Firefox[/green]")
            else:
                # Fallback to Chrome
                cookies = cookie_manager.auto_extract(browser='chrome')
                if cookies:
                    cookie_manager.save_cookies(cookies, profile_name)
                    if verbose:
                        console.print(f"[green]✓ Extracted and saved {len(cookies)} cookies from Chrome[/green]")
        except Exception as e:
            if verbose:
                console.print(f"[yellow]Browser extraction failed: {e}[/yellow]")
    
    driver = GrokWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True,
        debug_mode=debug
    )
    
    if cookies:
        driver.set_cookies(cookies)
    
    try:
        if debug:
            console.print("[cyan]🚀 Starting browser automation...[/cyan]")
        driver.start(debug_network=debug)
        
        import time
        
        # Track timing for each step
        step_times = {}
        overall_start = time.time()
        
        if debug:
            console.print("[cyan]🌐 Navigating to Grok.com...[/cyan]")
        nav_start = time.time()
        driver.navigate_to_grok()
        step_times['navigate'] = time.time() - nav_start
        if debug:
            console.print(f"[dim]⏱ Navigation took: {step_times['navigate']:.2f}s[/dim]")
        
        # Check if logged in
        login_check_start = time.time()
        is_logged_in = driver.is_logged_in()
        step_times['login_check'] = time.time() - login_check_start
        if debug:
            console.print(f"[dim]⏱ Login check took: {step_times['login_check']:.2f}s[/dim]")
        
        if not is_logged_in:
            if headless:
                if debug:
                    console.print("\n[yellow]⚠ Not logged in and running in headless mode[/yellow]")
                    console.print("[yellow]💡 Try: grok extract-cookies --browser chrome --profile from_headers[/yellow]")
                    console.print("[yellow]   Or run without --headless to login interactively[/yellow]")
                driver.close()
                return
            else:
                if debug:
                    console.print("\n[yellow]⚠ Not logged in - please log in to Grok in the browser window[/yellow]")
                console.print("[cyan]Waiting for login...[/cyan]")
                if debug:
                    console.print("[dim]Or press Ctrl+C and run: grok extract-cookies --browser chrome[/dim]")
                wait_login_start = time.time()
                if not driver.wait_for_login():
                    console.print("\n[yellow]⚠ Login timeout[/yellow]")
                    console.print("[yellow]💡 Tip: Extract cookies from your regular browser instead:[/yellow]")
                    console.print("[yellow]   grok extract-cookies --browser chrome --profile from_headers[/yellow]")
                    driver.close()
                    return
                step_times['wait_login'] = time.time() - wait_login_start
                if debug:
                    console.print(f"[dim]⏱ Wait for login took: {step_times['wait_login']:.2f}s[/dim]")
        
        # Save cookies
        cookie_save_start = time.time()
        new_cookies = driver.get_cookies()
        if new_cookies:
            cookie_manager.save_cookies(new_cookies, profile_name)
            if debug:
                console.print(f"[green]✓ Saved {len(new_cookies)} cookies to profile: {profile_name}[/green]")
        step_times['cookie_save'] = time.time() - cookie_save_start
        if debug:
            console.print(f"[dim]⏱ Cookie save took: {step_times['cookie_save']:.2f}s[/dim]")
        
        # Set model if specified
        if model and model != "auto":
            if debug:
                console.print(f"[cyan]Setting model to: {get_model_display_name(model)}...[/cyan]")
            model_start = time.time()
            model_set = driver.set_model(model)
            step_times['set_model'] = time.time() - model_start
            if debug:
                console.print(f"[dim]⏱ Set model took: {step_times['set_model']:.2f}s[/dim]")
            if not model_set:
                console.print(f"[yellow]⚠ Warning: Could not set model via UI. API will use: {model_name} ({model_mode})[/yellow]")
            elif debug:
                console.print(f"[green]✓ Model set successfully[/green]")
        
        # Enter message in chat box first (but don't send)
        if debug:
            console.print(f"[cyan]Entering message in chat box...[/cyan]")
        enter_msg_start = time.time()
        message_entered = driver.enter_message(message)
        step_times['enter_message'] = time.time() - enter_msg_start
        if debug:
            console.print(f"[dim]⏱ Enter message took: {step_times['enter_message']:.2f}s[/dim]")
        if not message_entered:
            console.print(f"[yellow]⚠ Warning: Could not enter message in chat box[/yellow]")
            driver.close()
            return
        
        # Re-verify model selection after entering message (model might have reverted)
        if model and model != "auto" and model_set:
            if debug:
                console.print(f"[cyan]Re-verifying model selection after entering message...[/cyan]")
            model_verify_start = time.time()
            model_still_selected = driver.verify_model_selection(model)
            step_times['model_verify'] = time.time() - model_verify_start
            if not model_still_selected:
                console.print(f"[yellow]⚠ Warning: Model appears to have reverted, attempting to re-select...[/yellow]")
                # Try to re-select the model
                model_reselect_start = time.time()
                model_reselected = driver.set_model(model)
                step_times['model_reselect'] = time.time() - model_reselect_start
                if model_reselected:
                    console.print(f"[green]✓ Model re-selected successfully[/green]")
                else:
                    console.print(f"[yellow]⚠ Could not re-select model, continuing with current selection...[/yellow]")
            elif debug:
                console.print(f"[green]✓ Model still selected correctly[/green]")
                console.print(f"[dim]⏱ Model verification took: {step_times['model_verify']:.2f}s[/dim]")
        
        # Wait briefly before toggling DeepSearch/Private
        if deepsearch or private:
            if debug:
                console.print(f"[cyan]Waiting 0.2s before toggling options...[/cyan]")
            time.sleep(0.2)  # OPTIMIZED: Reduced from 0.5s to 0.2s
            step_times['wait_before_toggles'] = 0.2
        
        # Enable DeepSearch if specified
        if deepsearch:
            if debug:
                console.print(f"[cyan]Enabling DeepSearch mode...[/cyan]")
            deepsearch_start = time.time()
            deepsearch_enabled = driver.enable_deepsearch()
            step_times['enable_deepsearch'] = time.time() - deepsearch_start
            if debug:
                console.print(f"[dim]⏱ Enable DeepSearch took: {step_times['enable_deepsearch']:.2f}s[/dim]")
            if not deepsearch_enabled:
                if debug:
                    console.print(f"[yellow]⚠ Warning: Could not enable DeepSearch - continuing with normal search[/yellow]")
            elif debug:
                console.print(f"[green]✓ DeepSearch enabled[/green]")
        
        # Enable Private mode if specified
        if private:
            if debug:
                console.print(f"[cyan]Enabling Private mode...[/cyan]")
            private_start = time.time()
            private_set = driver.set_private_mode(enable=True)
            step_times['enable_private'] = time.time() - private_start
            if debug:
                console.print(f"[dim]⏱ Enable Private took: {step_times['enable_private']:.2f}s[/dim]")
            if not private_set:
                console.print(f"[yellow]⚠ Warning: Could not enable Private mode[/yellow]")
            elif debug:
                console.print(f"[green]✓ Private mode enabled[/green]")
        
        # Send message
        if debug:
            console.print(f"[cyan]Sending message...[/cyan]")
        send_start = time.time()
        response_text = driver.send_message(wait_for_response=True)
        step_times['send_message'] = time.time() - send_start
        if debug:
            console.print(f"[dim]⏱ Send message took: {step_times['send_message']:.2f}s[/dim]")
        
        # Print timing summary
        if debug:
            total_time = time.time() - overall_start
            console.print(f"\n[bold cyan]⏱ Timing Summary:[/bold cyan]")
            console.print(f"[dim]  Navigation: {step_times.get('navigate', 0):.2f}s[/dim]")
            console.print(f"[dim]  Login check: {step_times.get('login_check', 0):.2f}s[/dim]")
            if 'wait_login' in step_times:
                console.print(f"[dim]  Wait login: {step_times['wait_login']:.2f}s[/dim]")
            console.print(f"[dim]  Cookie save: {step_times.get('cookie_save', 0):.2f}s[/dim]")
            if 'set_model' in step_times:
                console.print(f"[dim]  Set model: {step_times['set_model']:.2f}s[/dim]")
            console.print(f"[dim]  Enter message: {step_times.get('enter_message', 0):.2f}s[/dim]")
            if 'wait_before_toggles' in step_times:
                console.print(f"[dim]  Wait before toggles: {step_times['wait_before_toggles']:.2f}s[/dim]")
            if 'enable_deepsearch' in step_times:
                console.print(f"[dim]  Enable DeepSearch: {step_times['enable_deepsearch']:.2f}s[/dim]")
            if 'enable_private' in step_times:
                console.print(f"[dim]  Enable Private: {step_times['enable_private']:.2f}s[/dim]")
            console.print(f"[dim]  Send message: {step_times.get('send_message', 0):.2f}s[/dim]")
            console.print(f"[bold]  Total (before response): {total_time:.2f}s[/bold]")
            
            # Calculate time from navigation to entering message
            nav_to_enter = step_times.get('navigate', 0) + step_times.get('login_check', 0) + \
                          step_times.get('wait_login', 0) + step_times.get('cookie_save', 0) + \
                          step_times.get('set_model', 0) + step_times.get('enter_message', 0)
            console.print(f"[bold yellow]  Navigation → Enter message: {nav_to_enter:.2f}s[/bold yellow]")
        
        if response_text:
            # Create response object for consistent formatting
            try:
                from src.core.models import ChatResponse
            except ImportError:
                from core.models import ChatResponse
            response = ChatResponse(message=response_text)
            
            _display_response(response, format)
            
            if output:
                _save_output(response, output, format)
                console.print(f"\n[green]✓ Saved to: {output}[/green]")
        else:
            console.print("[yellow]⚠ No response received[/yellow]")
        
        # Keep browser open if requested
        if keep_browser_open:
            if not headless:
                console.print("\n[yellow]Browser will remain open - press Ctrl+C to close[/yellow]")
                driver.interactive_mode()
            else:
                console.print("\n[yellow]⚠ --keep-browser-open requires non-headless mode[/yellow]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        if verbose:
            import traceback
            console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        raise
    finally:
        if not keep_browser_open:
            driver.close()


def _display_response(response, format):
    """Display chat response in specified format with polished markdown rendering"""
    if format == 'json':
        console.print_json(json.dumps(response.to_dict(), indent=2))
        return
    elif format == 'markdown':
        # Use enhanced markdown rendering even for markdown format
        _display_markdown_response(response)
        return
    
    # Text format with enhanced markdown rendering
    _display_markdown_response(response)


def _display_markdown_response(response):
    """Display response with enhanced markdown rendering and colors"""
    import re
    import logging
    
    # Disable markdown parser debug logging
    markdown_logger = logging.getLogger('markdown_it')
    old_level = markdown_logger.level
    markdown_logger.setLevel(logging.WARNING)
    
    from rich.theme import Theme
    from rich.console import Console as RichConsole
    
    message = response.message.strip()
    
    if not message:
        console.print("[yellow]No response content[/yellow]")
        return
    
    # Clean up message - remove UI elements
    lines = message.split('\n')
    cleaned_lines = []
    skip_ui_elements = ['account', 'upgrade', 'install', 'download']
    
    for line in lines:
        line_lower = line.lower().strip()
        # Skip obvious UI elements
        if any(ui in line_lower for ui in skip_ui_elements) and len(line_lower) < 30:
            continue
        # Skip if line is just "###" followed by long query text
        if line.startswith('###') and len(line) > 100:
            continue
        cleaned_lines.append(line)
    
    message = '\n'.join(cleaned_lines).strip()
    
    # Extract inline links for reference section
    inline_links = []
    link_pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
    for match in re.finditer(link_pattern, message):
        link_text = match.group(1)
        link_url = match.group(2)
        if link_url.startswith('http'):
            inline_links.append({'text': link_text, 'url': link_url})
    
    # Clean up markdown tables by removing inline links
    def clean_table_cells(text):
        """Remove markdown links from table cells for cleaner display"""
        lines = text.split('\n')
        cleaned_lines = []
        in_table = False
        
        for line in lines:
            if '|' in line and not line.strip().startswith('```'):
                in_table = True
                cleaned_line = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)
                cleaned_lines.append(cleaned_line)
            else:
                if in_table and line.strip() == '':
                    in_table = False
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    message = clean_table_cells(message)
    
    # Enhanced color theme for better readability (no boxes for headings)
    custom_theme = Theme({
        "markdown.h1": "bold bright_cyan",
        "markdown.h2": "bold cyan",
        "markdown.h3": "bold bright_yellow",
        "markdown.h4": "bold yellow",
        "markdown.h5": "bold bright_white",
        "markdown.h6": "bold white",
        "markdown.link": "bright_green underline",
        "markdown.link_url": "dim green",
        "markdown.code": "bright_magenta on black",
        "markdown.code_block": "bright_white on black",
        "markdown.block_code": "bright_white on black",
        "markdown.item.bullet": "bright_cyan",
        "markdown.item.number": "bright_cyan",
        "markdown.block_quote": "dim italic bright_blue",
        "markdown.strong": "bold bright_white",
        "markdown.em": "italic bright_white",
        "markdown.strikethrough": "strike dim",
        "markdown.rule": "dim white",
        "markdown.table.border": "dim white",
        "markdown.table.header": "bold bright_cyan",
        "markdown.table.cell": "white",
    })
    
    # Disable Rich's default heading boxes by removing heading markers
    # This prevents the rectangular blocks around headings
    message = re.sub(r'^#{1,6}\s+(.+)$', r'\1', message, flags=re.MULTILINE)
    
    # Create themed console
    themed_console = RichConsole(theme=custom_theme, force_terminal=True)
    
    # Process and display message with syntax highlighting for code blocks (no header banner)
    # Message already has headings stripped above
    message = message.strip()
    _process_code_blocks(message, themed_console)
    
    # Restore logging level
    markdown_logger.setLevel(old_level)
    
    # Display sources/references
    all_references = []
    seen_urls = set()
    
    # Add inline links
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
    
    # Add sources
    if response.sources:
        for source in response.sources:
            url = source.get('url', '') if isinstance(source, dict) else getattr(source, 'url', '')
            title = source.get('title', 'N/A') if isinstance(source, dict) else getattr(source, 'title', 'N/A')
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_references.append({
                    'title': title,
                    'url': url,
                    'type': 'source'
                })
    
    # Display references
    if all_references:
        console.print("\n[bold bright_white on bright_cyan] ════════════════════════════════════════════════════════════ [/bold bright_white on bright_cyan]")
        console.print("[bold bright_white on bright_cyan]  REFERENCES                                                       [/bold bright_white on bright_cyan]")
        console.print("[bold bright_white on bright_cyan] ════════════════════════════════════════════════════════════ [/bold bright_white on bright_cyan]\n")
        
        for idx, ref in enumerate(all_references, 1):
            title = ref['title']
            url = ref['url']
            
            # Shorten long URLs
            display_url = url
            if len(url) > 80:
                from urllib.parse import urlparse
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc
                    path = parsed.path
                    if len(path) > 50:
                        display_url = f"{parsed.scheme}://{domain}{path[:30]}...{path[-15:]}"
                except (ValueError, AttributeError, Exception):
                    display_url = url[:75] + "..."
            
            if url and url != title:
                console.print(f"  [bright_cyan]{idx}.[/bright_cyan] [bold bright_white]{title}[/bold bright_white]")
                console.print(f"      [link={url}][dim bright_green]{display_url}[/dim bright_green][/link]")
            else:
                console.print(f"  [bright_cyan]{idx}.[/bright_cyan] [bold bright_white]{title}[/bold bright_white]")
        console.print()
    
    # Display follow-up suggestions
    if response.follow_up_suggestions:
        console.print("\n[bold bright_white on bright_yellow] ════════════════════════════════════════════════════════════ [/bold bright_white on bright_yellow]")
        console.print("[bold bright_white on bright_yellow]  FOLLOW-UP SUGGESTIONS                                            [/bold bright_white on bright_yellow]")
        console.print("[bold bright_white on bright_yellow] ════════════════════════════════════════════════════════════ [/bold bright_white on bright_yellow]\n")
        
        for idx, suggestion in enumerate(response.follow_up_suggestions, 1):
            label = suggestion.get('label', 'N/A') if isinstance(suggestion, dict) else getattr(suggestion, 'label', 'N/A')
            console.print(f"  [bright_yellow]{idx}.[/bright_yellow] [italic bright_white]{label}[/italic bright_white]")
        console.print()
    
    # Metadata footer
    console.print()
    metadata_parts = []
    metadata_parts.append(f"[dim cyan]Response:[/dim cyan] [bright_white]{len(message)} chars[/bright_white]")
    if all_references:
        metadata_parts.append(f"[dim cyan]References:[/dim cyan] [bright_white]{len(all_references)}[/bright_white]")
    if response.model:
        metadata_parts.append(f"[dim cyan]Model:[/dim cyan] [bright_white]{response.model}[/bright_white]")
    console.print("[dim]" + " | ".join(metadata_parts) + "[/dim]\n")


def _process_code_blocks(text, themed_console):
    """Process markdown and render code blocks with syntax highlighting"""
    import re
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    
    # Split text into code blocks and regular markdown
    code_block_pattern = r'```(\w+)?\n(.*?)```'
    
    parts = []
    last_end = 0
    
    for match in re.finditer(code_block_pattern, text, re.DOTALL):
        # Add text before code block
        before = text[last_end:match.start()]
        if before.strip():
            parts.append(('markdown', before))
        
        # Add code block
        language = match.group(1) or 'text'
        code = match.group(2)
        parts.append(('code', language, code))
        
        last_end = match.end()
    
    # Add remaining text
    if last_end < len(text):
        remaining = text[last_end:]
        if remaining.strip():
            parts.append(('markdown', remaining))
    
    # Render parts
    if not parts:
        # No code blocks, just render as markdown (but strip headings to avoid boxes)
        # Remove any remaining headings that might create boxes
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        md = Markdown(text)
        themed_console.print(md)
    else:
        for part in parts:
            if part[0] == 'markdown':
                # Remove headings from markdown parts to avoid boxes
                markdown_text = re.sub(r'^#{1,6}\s+', '', part[1], flags=re.MULTILINE)
                md = Markdown(markdown_text)
                themed_console.print(md)
            elif part[0] == 'code':
                language = part[1]
                code = part[2]
                # Try to detect language if not specified
                if language == 'text' or not language:
                    # Try to detect from code content
                    if 'def ' in code or 'import ' in code or 'from ' in code:
                        language = 'python'
                    elif 'function ' in code or 'const ' in code or 'let ' in code:
                        language = 'javascript'
                    elif 'SELECT ' in code or 'FROM ' in code:
                        language = 'sql'
                    elif '<html' in code or '<div' in code:
                        language = 'html'
                    elif 'package ' in code or 'public class' in code:
                        language = 'java'
                    else:
                        language = 'text'
                
                try:
                    syntax = Syntax(
                        code,
                        language,
                        theme="monokai",
                        line_numbers=False,
                        word_wrap=True
                    )
                    themed_console.print(syntax)
                except (ValueError, Exception):
                    # Fallback if syntax highlighting fails
                    themed_console.print(f"[bright_white on black]{code}[/bright_white on black]")
    
    return text


def _save_output(response, filepath, format):
    """Save response to file"""
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    if format == 'json':
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(response.to_dict(), f, indent=2)
    elif format == 'markdown':
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.to_markdown())
    else:  # text
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(response.message)


@cli.command()
@click.option('--profile', '-p', help='Profile name')
@click.option('--headless', is_flag=True, help='Run in headless mode')
@click.option('--persistent', is_flag=True, help='Use persistent session')
def login(profile, headless, persistent):
    """
    Login to Grok and save cookies
    
    Opens browser for you to login, then saves cookies for future use.
    
    Example:
        grok login --profile my_account
    """
    from pathlib import Path
    
    console.print("\n[bold cyan]Grok Login[/bold cyan]\n")
    
    # Setup persistent browser profile
    user_data_dir = None
    if persistent:
        profile_name = profile or "default"
        user_data_dir = f"browser_data/{profile_name}"
        Path(user_data_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[green]✓ Using persistent session: {user_data_dir}[/green]")
    
    driver = GrokWebDriver(
        headless=headless,
        user_data_dir=user_data_dir,
        stealth_mode=True
    )
    
    try:
        console.print("[cyan]Opening browser...[/cyan]")
        driver.start()
        driver.navigate_to_grok()
        
        if not driver.is_logged_in():
            if headless:
                console.print("\n[yellow]⚠ Cannot login in headless mode[/yellow]")
                console.print("[yellow]⚠ Please run without --headless flag[/yellow]")
                driver.close()
                return
            
            console.print("\n[yellow]Please log in to Grok in the browser window[/yellow]")
            console.print("[cyan]Waiting for login...[/cyan]")
            
            if driver.wait_for_login():
                console.print("[green]✓ Login detected![/green]")
            else:
                console.print("[yellow]⚠ Login timeout[/yellow]")
                driver.close()
                return
        else:
            console.print("[green]✓ Already logged in![/green]")
        
        # Extract and save cookies
        cookies = driver.get_cookies()
        if cookies:
            cookie_manager = CookieManager()
            profile_name = profile or "default"
            cookie_manager.save_cookies(cookies, profile_name)
            console.print(f"\n[green]✓ Cookies saved to profile: {profile_name}[/green]")
            console.print(f"\n[bold]You can now use:[/bold]")
            console.print(f"  grok chat \"your message\" --profile {profile_name}")
        else:
            console.print("[yellow]⚠ No cookies found[/yellow]")
        
        if not headless:
            console.print("\n[yellow]Press Ctrl+C to close browser...[/yellow]")
            driver.interactive_mode()
    
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
    except Exception as e:
        console.print(f"\n[red]✗ Error: {str(e)}[/red]")
        raise
    finally:
        driver.close()


@cli.command('list-profiles')
def list_profiles():
    """List all saved cookie profiles"""
    cookie_manager = CookieManager()
    profiles = cookie_manager.list_profiles()
    
    if not profiles:
        console.print("[yellow]No saved profiles[/yellow]")
        return
    
    console.print("\n[bold cyan]Saved Cookie Profiles:[/bold cyan]\n")
    for profile in profiles:
        console.print(f"  • {profile}")


@cli.command('extract-cookies')
@click.option('--browser', '-b', type=click.Choice(['chrome', 'firefox', 'edge']), 
              default='firefox', help='Browser to extract from (default: firefox)')
@click.option('--profile', '-p', help='Profile name to save as')
@click.option('--profile-path', help='Custom browser profile path (for Chrome)')
def extract_cookies(browser, profile, profile_path):
    """
    Extract cookies from your existing browser
    
    This extracts cookies from your regular browser (Chrome, Firefox, Edge)
    where you're already logged into Grok. No need to login in Playwright browser!
    
    Example:
        grok extract-cookies --browser chrome --profile my_account
    """
    console.print(f"\n[cyan]Extracting cookies from {browser}...[/cyan]")
    console.print("[yellow]⚠ Make sure your browser is completely closed![/yellow]")
    
    try:
        cookie_manager = CookieManager()
        
        if browser == 'chrome':
            if profile_path:
                cookies = CookieManager.extract_from_chrome(profile_path=profile_path)
            else:
                cookies = CookieManager.extract_from_chrome()
        elif browser == 'firefox':
            cookies = CookieManager.extract_from_firefox()
        elif browser == 'edge':
            cookies = CookieManager.extract_from_edge()
        else:
            console.print(f"[red]✗ Unsupported browser: {browser}[/red]")
            return
        
        if not cookies:
            console.print("[red]✗ No cookies found for grok.com[/red]")
            console.print("[yellow]Make sure you:[/yellow]")
            console.print("  1. Have visited https://grok.com")
            console.print("  2. Are logged into your account")
            console.print("  3. Browser is completely closed")
            return
        
        console.print(f"[green]✓ Extracted {len(cookies)} cookies[/green]")
        
        if profile:
            cookie_manager.save_cookies(cookies, name=profile)
            console.print(f"[green]✓ Saved as profile: {profile}[/green]")
            console.print(f"\n[bold]You can now use:[/bold]")
            console.print(f"  grok chat \"your message\" --profile {profile}")
        else:
            console.print("\n[yellow]Cookies (first 5):[/yellow]")
            for idx, (key, value) in enumerate(list(cookies.items())[:5], 1):
                console.print(f"  {idx}. {key}: {value[:30]}...")
            console.print("\n[yellow]⚠ Cookies not saved! Use --profile to save them.[/yellow]")
    
    except ImportError as e:
        console.print(f"[red]✗ Missing dependency: {e}[/red]")
        console.print("[yellow]💡 Install: pip install browser-cookie3[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {str(e)}[/red]")
        console.print("\n[yellow]Troubleshooting:[/yellow]")
        console.print("  1. Close browser completely (check Task Manager)")
        console.print("  2. Make sure you're logged into Grok.com")
        console.print("  3. Try a different browser (--browser firefox)")


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()

