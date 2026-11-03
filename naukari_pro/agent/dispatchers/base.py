"""
naukariPro Agent Platform Dispatchers: Base Protocols & Data Models
Module: naukari_pro.agent.dispatchers.base

Provides:
- PlatformExecutionReport: Standardized execution metrics and application records.
- PlatformDispatcher: Runtime-checkable Protocol for platform dispatchers.
- BasePlatformDispatcher: Common base class providing timeout guards and error resilience.
"""

from __future__ import annotations

import logging
import time
import concurrent.futures
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:
    from naukari_pro.agent.intent import CandidateIntent

logger = logging.getLogger("naukariPro.Agent.Dispatchers")


# ==============================================================================
# 1. STANDARDIZED EXECUTION REPORT
# ==============================================================================

@dataclass
class PlatformExecutionReport:
    """
    Standardized execution summary emitted by all platform dispatchers.
    Captures volume, outcomes, granular job records, and error diagnostics.
    """
    platform_name: str
    total_evaluated: int = 0
    submitted_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    dedup_skipped_count: int = 0
    dry_run: bool = False
    duration_seconds: float = 0.0
    records: List[Dict[str, Any]] = field(default_factory=list)
    applied_jobs: List[Dict[str, Any]] = field(default_factory=list)
    skipped_jobs: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Backward compatibility property aliases
    @property
    def total_applied(self) -> int:
        return self.submitted_count

    @total_applied.setter
    def total_applied(self, val: int) -> None:
        self.submitted_count = val

    @property
    def total_skipped(self) -> int:
        return self.skipped_count

    @total_skipped.setter
    def total_skipped(self, val: int) -> None:
        self.skipped_count = val

    @property
    def dedup_skipped(self) -> int:
        return self.dedup_skipped_count

    @dedup_skipped.setter
    def dedup_skipped(self, val: int) -> None:
        self.dedup_skipped_count = val

    def add_record(self, record: Dict[str, Any]) -> None:
        """Appends a job record and updates counters and lists based on status."""
        self.records.append(record)
        status = str(record.get("status", "")).upper()
        if "DUPLICATE" in status:
            self.dedup_skipped_count += 1
            self.skipped_count += 1
            self.skipped_jobs.append(record)
        elif "SUBMITTED" in status or "APPLIED" in status or "AUTO-FILLED" in status or "VALIDATED" in status:
            self.submitted_count += 1
            self.applied_jobs.append(record)
        elif "REJECTED" in status or "SKIPPED" in status or "GATED" in status:
            self.skipped_count += 1
            self.skipped_jobs.append(record)
        elif "FAILED" in status or "ERROR" in status:
            self.failed_count += 1
            self.skipped_jobs.append(record)
        else:
            # Default fallback for record tracking
            self.skipped_count += 1
            self.skipped_jobs.append(record)

    def add_error(self, error_message: str, fatal: bool = False) -> None:
        """Records an execution error message."""
        self.errors.append(str(error_message))
        if fatal:
            self.success = False

    def to_dict(self) -> Dict[str, Any]:
        """Serializes report to dictionary."""
        return asdict(self)

    def summary(self) -> str:
        """Formats single-line human-readable summary."""
        mode = "DRY-RUN" if self.dry_run else "LIVE"
        status_flag = "SUCCESS" if self.success else "FAILED"
        return (
            f"[{self.platform_name.upper()}] ({mode}|{status_flag}) - "
            f"Evaluated: {self.total_evaluated} | "
            f"Submitted: {self.submitted_count} | "
            f"Skipped: {self.skipped_count} (Dedup: {self.dedup_skipped_count}) | "
            f"Failed: {self.failed_count} | "
            f"Time: {self.duration_seconds:.2f}s"
        )


# ==============================================================================
# 2. PLATFORM DISPATCHER PROTOCOL
# ==============================================================================

@runtime_checkable
class PlatformDispatcher(Protocol):
    """Protocol defining the interface for all platform dispatcher adapters."""
    platform_name: str
    timeout_seconds: float

    def dispatch(self, intent: Any) -> PlatformExecutionReport:
        """Executes live or dry-run application workflow according to intent."""
        ...

    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        """Executes 100% offline dry-run without live browser or network calls."""
        ...


# ==============================================================================
# 3. BASE PLATFORM DISPATCHER (TIMEOUT & ERROR SHIELD)
# ==============================================================================

class BasePlatformDispatcher(ABC):
    """
    Abstract base class implementing the PlatformDispatcher protocol with
    built-in ThreadPoolExecutor timeout enforcement, error shielding, and dry-run delegation.
    """
    platform_name: str = "base"
    default_timeout_seconds: float = 300.0  # 5 minutes default

    def __init__(self, timeout_seconds: Optional[float] = None):
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else self.default_timeout_seconds

    def execute_with_timeout(
        self,
        task_fn: Callable[[], PlatformExecutionReport],
        timeout_seconds: Optional[float] = None
    ) -> PlatformExecutionReport:
        """
        Executes a callable inside an isolated worker thread with strict timeout enforcement.
        Shields the caller from hanging processes and unhandled exceptions.
        """
        t_limit = timeout_seconds if timeout_seconds is not None else self.timeout_seconds
        start_time = time.time()

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(task_fn)
        try:
            report = future.result(timeout=t_limit)
            report.duration_seconds = time.time() - start_time
            executor.shutdown(wait=False, cancel_futures=True)
            return report
        except concurrent.futures.TimeoutError:
            elapsed = time.time() - start_time
            err_msg = f"Platform '{self.platform_name}' timed out after {elapsed:.1f}s (limit: {t_limit}s)"
            logger.error(err_msg)
            executor.shutdown(wait=False, cancel_futures=True)
            return PlatformExecutionReport(
                platform_name=self.platform_name,
                success=False,
                duration_seconds=elapsed,
                errors=[err_msg]
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            err_msg = f"Platform '{self.platform_name}' encountered unhandled exception: {type(exc).__name__}: {str(exc)}"
            logger.exception(err_msg)
            executor.shutdown(wait=False, cancel_futures=True)
            return PlatformExecutionReport(
                platform_name=self.platform_name,
                success=False,
                duration_seconds=elapsed,
                errors=[err_msg]
            )

    def dispatch(self, intent: Any) -> PlatformExecutionReport:
        """
        Public entrypoint. If intent.dry_run is True, routes immediately to dispatch_dry_run.
        Otherwise, executes live automation inside execute_with_timeout.
        """
        if getattr(intent, "dry_run", False):
            return self.dispatch_dry_run(intent)

        return self.execute_with_timeout(lambda: self._execute_live(intent))

    @abstractmethod
    def _execute_live(self, intent: Any) -> PlatformExecutionReport:
        """Protected method implemented by concrete dispatchers for live automation."""
        raise NotImplementedError

    @abstractmethod
    def dispatch_dry_run(self, intent: Any) -> PlatformExecutionReport:
        """100% offline dry-run execution implemented by concrete dispatchers."""
        raise NotImplementedError
