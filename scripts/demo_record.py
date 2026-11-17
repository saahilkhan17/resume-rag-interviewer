#!/usr/bin/env python3
"""Demo recording script for Resume RAG Interviewer.

- In normal mode it drives the frontend UI with Playwright, records a video, and saves it to demo/demo.mp4.
- With ``--smoke`` it only exercises the backend API (same flow as verify.sh) and prints ``SMOKE OK``.

The script is deliberately defensive: it checks that the backend and (if needed) the frontend are up before proceeding,
and it guards the optional Playwright import so that ``--smoke`` works without Playwright installed.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
import time
import shutil
import subprocess
from pathlib import Path

API_ROOT = "http://127.0.0.1:8000"
FRONTEND_ROOT = "http://localhost:5173"
SAMPLE_RESUME = Path(__file__).parent.parent / "backend" / "tests" / "fixtures" / "sample_resume.txt"
ANSWER_TEXT = (
    "Gradient descent updates parameters using the negative gradient scaled by the learning rate; "
    "mini-batch is the practical standard and Adam adds momentum with adaptive rates."
)

def check_backend():
    try:
        with urllib.request.urlopen(f"{API_ROOT}/health") as resp:
            data = json.load(resp)
            return data.get("status") == "ok"
    except Exception:
        return False

def check_frontend():
    try:
        with urllib.request.urlopen(FRONTEND_ROOT) as resp:
            return resp.status == 200
    except Exception:
        return False

def post_json(url, payload, expect_status=200):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        if resp.status != expect_status:
            raise RuntimeError(f"POST {url} returned {resp.status}, expected {expect_status}")
        return json.load(resp)

def get_json(url, expect_status=200):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req) as resp:
        if resp.status != expect_status:
            raise RuntimeError(f"GET {url} returned {resp.status}, expected {expect_status}")
        return json.load(resp)

def delete(url, expect_status=200):
    req = urllib.request.Request(url, method="DELETE")
    with urllib.request.urlopen(req) as resp:
        if resp.status != expect_status:
            raise RuntimeError(f"DELETE {url} returned {resp.status}, expected {expect_status}")

def smoke_flow():
    # Create session
    with open(SAMPLE_RESUME, "rb") as f:
        resume_bytes = f.read()
    # multipart form via urllib is cumbersome; reuse curl via subprocess for brevity
    import subprocess, shlex, tempfile
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp.write(resume_bytes)
        tmp_path = tmp.name
    try:
        cmd = [
            "curl",
            "-s",
            "-X",
            "POST",
            "-F",
            f"resume=@{tmp_path}",
            "-F",
            "role=ai-ml-engineer",
            f"{API_ROOT}/api/sessions",
        ]
        result = subprocess.check_output(cmd)
        create_resp = json.loads(result)
    finally:
        os.unlink(tmp_path)
    session_id = create_resp["session_id"]

    # GET roles
    get_json(f"{API_ROOT}/api/roles")

    # Start session
    start_resp = post_json(f"{API_ROOT}/api/sessions/{session_id}/start", {}, expect_status=200)
    question_ids = [q["id"] for q in start_resp.get("questions", [])]
    if not question_ids:
        raise RuntimeError("No questions returned from start")

    # Answer each question
    for qid in question_ids:
        post_json(
            f"{API_ROOT}/api/sessions/{session_id}/answers",
            {"question_id": qid, "answer_text": ANSWER_TEXT},
            expect_status=201,
        )

    # Complete session
    complete_resp = post_json(f"{API_ROOT}/api/sessions/{session_id}/complete", {}, expect_status=200)
    summary = complete_resp.get("summary", {})
    if not summary.get("overall_assessment"):
        raise RuntimeError("Overall assessment missing in summary")
    if len(summary.get("per_question", [])) != len(question_ids):
        raise RuntimeError("Per-question count mismatch")

    # GET summary and session detail
    get_json(f"{API_ROOT}/api/sessions/{session_id}/summary")
    sess = get_json(f"{API_ROOT}/api/sessions/{session_id}")
    if sess.get("question_count") != len(question_ids):
        raise RuntimeError("Session detail question_count mismatch")

    # Delete session
    delete(f"{API_ROOT}/api/sessions/{session_id}")

    print("SMOKE OK")

def find_first(page, selectors, timeout=5000, step_name=""):
    """Return the first locator that becomes visible.
    Each selector is a zero‑arg callable that receives the page and returns a Locator.
    The function waits for the locator to be visible within `timeout` ms. If it times out,
    the next selector is tried. If none match, a RuntimeError is raised naming the step.
    """
    for sel in selectors:
        try:
            loc = sel(page)
            # wait_for will raise TimeoutError if not visible in time
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    raise RuntimeError(f"No matching selector found for {step_name}")
    """Return the first locator that becomes visible.
    Each selector is a zero‑arg callable that receives the page and returns a Locator.
    The function waits for the locator to be visible within `timeout` ms. If it times out,
    the next selector is tried. If none match, a RuntimeError is raised naming the step.
    """
    for sel in selectors:
        try:
            loc = sel(page)
            # wait_for will raise TimeoutError if not visible in time
            loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    raise RuntimeError(f"No matching selector found for {step_name}")
    """Return the first matching element using the supplied selector list.
    Each selector is a lambda that receives the page and should either return an element or raise.
    """
    for sel in selectors:
        try:
            return sel(page)
        except Exception:
            continue
    raise RuntimeError("No matching selector found")

def ui_flow():
    # Import Playwright lazily; exit with a helpful message if not installed.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Install it to run the UI demo.", file=sys.stderr)
        sys.exit(1)

    headed = os.getenv("DEMO_HEADED") == "1"
    video_dir = Path("demo")
    video_dir.mkdir(exist_ok=True)
    # Record existing .webm files to identify new ones later
    existing_videos = set(video_dir.glob("*.webm"))

    step = "setup"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=not headed)
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                record_video_dir=str(video_dir),
                record_video_size={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Backend / Frontend health checks
            step = "backend health check"
            if not check_backend():
                print("Backend health check failed.", file=sys.stderr)
                sys.exit(1)
            step = "frontend health check"
            if not check_frontend():
                print(f"Frontend not reachable at {FRONTEND_ROOT}.", file=sys.stderr)
                sys.exit(1)

            # Navigate to UI
            step = "navigate to UI"
            page.goto(FRONTEND_ROOT)

            # Role selection
            step = "role selection"
            role_btn = find_first(
                page,
                [
                    lambda p: p.locator(".role-card", has_text="AI/ML Engineer"),
                    lambda p: p.get_by_text("AI/ML Engineer"),
                ],
                timeout=10000,
                step_name="role selection",
            )
            role_btn.click()

            # Upload resume
            step = "upload resume"
            file_input = page.locator('input[type="file"]')
            file_input.set_input_files(str(SAMPLE_RESUME))

            # Create session
            step = "create session"
            create_btn = find_first(
                page,
                [lambda p: p.get_by_role("button", name="Upload resume & create session")],
                timeout=10000,
                step_name="create session",
            )
            create_btn.click()

            # Wait for Start interview button
            step = "wait for Start interview"
            start_btn = find_first(
                page,
                [lambda p: p.get_by_role("button", name="Start interview")],
                timeout=15000,
                step_name="wait for Start interview",
            )
            start_btn.click()

            # Wait for first question textarea
            step = "wait for first question"
            answer_box = find_first(
                page,
                [
                    lambda p: p.get_by_role("textbox", name="interview-answer"),
                    lambda p: p.locator("#interview-answer"),
                    lambda p: p.get_by_placeholder("Type your detailed technical answer here..."),
                ],
                timeout=15000,
                step_name="wait for first question",
            )

            # Answer loop (5 questions)
            for i in range(5):
                # Fill answer
                answer_box = find_first(
                    page,
                    [
                        lambda p: p.get_by_role("textbox", name="interview-answer"),
                        lambda p: p.locator("#interview-answer"),
                        lambda p: p.get_by_placeholder("Type your detailed technical answer here..."),
                    ],
                    timeout=10000,
                    step_name=f"answer box Q{i+1}",
                )
                answer_box.fill(ANSWER_TEXT)

                if i < 4:
                    step = f"save & next Q{i+1}"
                    save_next_btn = find_first(
                        page,
                        [lambda p: p.get_by_role("button", name="Save & Next")],
                        timeout=10000,
                        step_name=step,
                    )
                    save_next_btn.click()
                else:
                    step = "save last answer"
                    save_btn = find_first(
                        page,
                        [lambda p: p.get_by_role("button", name="Save answer")],
                        timeout=10000,
                        step_name=step,
                    )
                    save_btn.click()
                    time.sleep(1)
                    step = "finish interview"
                    finish_btn = find_first(
                        page,
                        [
                            lambda p: p.get_by_role("button", name="Finish & get summary"),
                            lambda p: p.get_by_role("button", name="Finish"),
                        ],
                        timeout=15000,
                        step_name=step,
                    )
                    finish_btn.click()
                time.sleep(1)

            # Wait for results view
            step = "wait for results"
            # Accept either heading or overall assessment text
            try:
                page.wait_for_selector("text=Interview Evaluation & Results", timeout=15000)
            except Exception:
                page.wait_for_selector("text=Overall Assessment", timeout=15000)
            time.sleep(2)

            # Cleanup Playwright resources
            context.close()
            browser.close()
    except Exception as e:
        print(f"FAILED at {step}: {e}", file=sys.stderr)
        # Ensure browser/context are closed defensively (ignore if already closed)
        try:
            context.close()
        except Exception:
            pass
        try:
            browser.close()
        except Exception:
            pass
        # Delete any newly created .webm files for this run
        new_videos = set(video_dir.glob("*.webm")) - existing_videos
        for nv in new_videos:
            try:
                nv.unlink()
            except Exception:
                pass
        sys.exit(1)

    # After successful run, locate new video file(s)
    new_videos = list(set(video_dir.glob("*.webm")) - existing_videos)
    if not new_videos:
        print("No video was recorded.")
        sys.exit(1)
    if len(new_videos) != 1:
        print(f"Unexpected number of new video files: {len(new_videos)}")
        sys.exit(1)
    recorded = new_videos[0]
    final_path = video_dir / "demo.mp4"
    if shutil.which("ffmpeg"):
        try:
            subprocess.run(["ffmpeg", "-y", "-i", str(recorded), str(final_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            recorded.unlink()
            print(f"Demo video saved to {final_path}")
        except Exception:
            print(f"ffmpeg conversion failed; keeping original webm at {recorded}")
    else:
        print(f"ffmpeg not found; demo recorded as {recorded}")
    # Import Playwright lazily; exit with a helpful message if not installed.
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is not installed. Install it to run the UI demo.", file=sys.stderr)
        sys.exit(1)

    headed = os.getenv("DEMO_HEADED") == "1"
    video_dir = Path("demo")
    video_dir.mkdir(exist_ok=True)
    video_path = video_dir / "demo.webm"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, record_video_dir=str(video_dir), record_video_size={"width": 1280, "height": 800})
        page = context.new_page()

        # Verify backend health
        if not check_backend():
            print("Backend health check failed.", file=sys.stderr)
            sys.exit(1)
        # Verify frontend reachable
        if not check_frontend():
            print("Frontend not reachable at {FRONTEND_ROOT}.", file=sys.stderr)
            sys.exit(1)

        # Navigate to UI
        page.goto(FRONTEND_ROOT)

        # Upload resume
        file_input = page.locator('input[type="file"]')
        file_input.set_input_files(str(SAMPLE_RESUME))

        # Select role (using robust selectors)
        try:
            role_btn = find_first(page, [
                lambda p: p.get_by_role("button", name="AI/ML Engineer"),
                lambda p: p.get_by_text("AI/ML Engineer")
            ])
            role_btn.click()
        except Exception as e:
            print(f"Failed at role selection step: {e}", file=sys.stderr)
            sys.exit(1)

        # Start interview (robust)
        try:
            start_btn = find_first(page, [
                lambda p: p.get_by_role("button", name="Start interview"),
                lambda p: p.get_by_role("button", name="Start"),
                lambda p: p.get_by_role("button", name="Begin interview")
            ])
            start_btn.click()
        except Exception as e:
            print(f"Failed at start step: {e}", file=sys.stderr)
            sys.exit(1)

        # Loop over 5 questions
        for i in range(5):
            # Wait for answer box (robust selectors)
            try:
                answer_box = find_first(page, [
                    lambda p: p.get_by_role("textbox"),
                    lambda p: p.locator("textarea"),
                    lambda p: p.get_by_placeholder("Answer..."),
                    lambda p: p.get_by_placeholder("Type your answer here")
                ])
                answer_box.fill(ANSWER_TEXT)
            except Exception as e:
                print(f"Failed at answer box step (question {i+1}): {e}", file=sys.stderr)
                sys.exit(1)
            # Submit / next button
            try:
                submit_btn = find_first(page, [
                    lambda p: p.get_by_role("button", name="Submit"),
                    lambda p: p.get_by_role("button", name="Next"),
                    lambda p: p.get_by_role("button", name="Save answer")
                ])
                submit_btn.click()
            except Exception as e:
                print(f"Failed at submit/next step (question {i+1}): {e}", file=sys.stderr)
                sys.exit(1)
            time.sleep(0.5)

        # Complete interview (robust)
        try:
            complete_btn = find_first(page, [
                lambda p: p.get_by_role("button", name="Complete"),
                lambda p: p.get_by_role("button", name="Finish"),
                lambda p: p.get_by_role("button", name="Complete interview"),
                lambda p: p.get_by_role("button", name="Submit interview")
            ])
            complete_btn.click()
        except Exception as e:
            print(f"Failed at complete step: {e}", file=sys.stderr)
            sys.exit(1)

        # Wait for summary view
        page.wait_for_selector("text=Summary", timeout=5000)
        time.sleep(2)
        # Close everything
        context.close()
        browser.close()

    # Playwright records a .webm file per page; rename the first one.
    recorded = next(video_dir.glob("*.webm"), None)
    if recorded:
        final_path = video_dir / "demo.mp4"
        # Try to convert with ffmpeg if available
        if shutil.which("ffmpeg"):
            try:
                subprocess.run(["ffmpeg", "-y", "-i", str(recorded), str(final_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                recorded.unlink()
                print(f"Demo video saved to {final_path}")
            except Exception:
                print(f"ffmpeg conversion failed; keeping original webm at {recorded}")
        else:
            # Keep .webm and inform user
            print(f"ffmpeg not found; demo recorded as {recorded}")
    else:
        print("No video was recorded.")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Record demo of Resume RAG Interviewer UI.")
    parser.add_argument("--smoke", action="store_true", help="Run API smoke test instead of UI automation.")
    args = parser.parse_args()

    if not check_backend():
        print("Backend health endpoint not reachable at http://127.0.0.1:8000/health", file=sys.stderr)
        sys.exit(1)

    if args.smoke:
        smoke_flow()
    else:
        if not check_frontend():
            print("Frontend not reachable at http://localhost:5173/", file=sys.stderr)
            sys.exit(1)
        ui_flow()

if __name__ == "__main__":
    main()
