"""
AI Model Management and Training Pipeline

This module provides comprehensive AI model management, training pipelines,
and model versioning for the customer service system.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings


class ModelType(Enum):
    """Types of AI models in the system."""
    CONVERSATIONAL = "conversational"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    INTENT_CLASSIFICATION = "intent_classification"
    ENTITY_EXTRACTION = "entity_extraction"
    RESPONSE_GENERATION = "response_generation"
    QUALITY_ASSESSMENT = "quality_assessment"


class ModelStatus(Enum):
    """Model deployment status."""
    TRAINING = "training"
    VALIDATING = "validating"
    READY = "ready"
    DEPLOYED = "deployed"
    DEPRECATED = "deprecated"
    FAILED = "failed"


@dataclass
class ModelMetrics:
    """Model performance metrics."""
    accuracy: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    response_time_ms: Optional[float] = None
    token_efficiency: Optional[float] = None
    user_satisfaction: Optional[float] = None
    custom_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ModelVersion:
    """Model version information."""
    version_id: str
    model_type: ModelType
    name: str
    description: str
    created_at: datetime
    status: ModelStatus
    metrics: ModelMetrics
    config: Dict[str, Any]
    artifacts_path: str
    created_by: str
    tags: List[str] = field(default_factory=list)
    parent_version_id: Optional[str] = None


@dataclass
class TrainingJob:
    """Training job configuration and status."""
    job_id: str
    model_type: ModelType
    config: Dict[str, Any]
    dataset_path: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    logs: List[str] = field(default_factory=list)
    error_message: Optional[str] = None
    result_metrics: Optional[ModelMetrics] = None


class ModelRegistry:
    """Registry for managing AI model versions and metadata."""
    
    def __init__(self, storage_path: str = "models"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.metadata_file = self.storage_path / "registry.json"
        self.models = self._load_registry()
        self.logger = logging.getLogger(__name__)
    
    def _load_registry(self) -> Dict[str, ModelVersion]:
        """Load model registry from storage."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    models = {}
                    for version_id, model_data in data.items():
                        models[version_id] = ModelVersion(
                            version_id=model_data['version_id'],
                            model_type=ModelType(model_data['model_type']),
                            name=model_data['name'],
                            description=model_data['description'],
                            created_at=datetime.fromisoformat(model_data['created_at']),
                            status=ModelStatus(model_data['status']),
                            metrics=ModelMetrics(**model_data['metrics']),
                            config=model_data['config'],
                            artifacts_path=model_data['artifacts_path'],
                            created_by=model_data['created_by'],
                            tags=model_data.get('tags', []),
                            parent_version_id=model_data.get('parent_version_id')
                        )
                    return models
            except Exception as e:
                self.logger.error(f"Error loading model registry: {e}")
                return {}
        return {}
    
    def _save_registry(self):
        """Save model registry to storage."""
        try:
            data = {}
            for version_id, model in self.models.items():
                data[version_id] = {
                    'version_id': model.version_id,
                    'model_type': model.model_type.value,
                    'name': model.name,
                    'description': model.description,
                    'created_at': model.created_at.isoformat(),
                    'status': model.status.value,
                    'metrics': {
                        'accuracy': model.metrics.accuracy,
                        'precision': model.metrics.precision,
                        'recall': model.metrics.recall,
                        'f1_score': model.metrics.f1_score,
                        'response_time_ms': model.metrics.response_time_ms,
                        'token_efficiency': model.metrics.token_efficiency,
                        'user_satisfaction': model.metrics.user_satisfaction,
                        'custom_metrics': model.metrics.custom_metrics
                    },
                    'config': model.config,
                    'artifacts_path': model.artifacts_path,
                    'created_by': model.created_by,
                    'tags': model.tags,
                    'parent_version_id': model.parent_version_id
                }
            
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Error saving model registry: {e}")
    
    def register_model(
        self,
        model_type: ModelType,
        name: str,
        description: str,
        config: Dict[str, Any],
        artifacts_path: str,
        created_by: str,
        tags: Optional[List[str]] = None,
        parent_version_id: Optional[str] = None,
        metrics: Optional[ModelMetrics] = None
    ) -> str:
        """Register a new model version."""
        
        # Generate version ID
        version_data = f"{model_type.value}:{name}:{datetime.utcnow().isoformat()}"
        version_id = hashlib.sha256(version_data.encode()).hexdigest()[:16]
        
        model_version = ModelVersion(
            version_id=version_id,
            model_type=model_type,
            name=name,
            description=description,
            created_at=datetime.utcnow(),
            status=ModelStatus.READY,
            metrics=metrics or ModelMetrics(),
            config=config,
            artifacts_path=artifacts_path,
            created_by=created_by,
            tags=tags or [],
            parent_version_id=parent_version_id
        )
        
        self.models[version_id] = model_version
        self._save_registry()
        
        self.logger.info(f"Registered model version: {version_id}")
        return version_id
    
    def get_model(self, version_id: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        return self.models.get(version_id)
    
    def list_models(
        self,
        model_type: Optional[ModelType] = None,
        status: Optional[ModelStatus] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelVersion]:
        """List models with optional filtering."""
        
        models = list(self.models.values())
        
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if status:
            models = [m for m in models if m.status == status]
        
        if tags:
            models = [m for m in models if any(tag in m.tags for tag in tags)]
        
        return sorted(models, key=lambda x: x.created_at, reverse=True)
    
    def update_model_status(self, version_id: str, status: ModelStatus):
        """Update model status."""
        if version_id in self.models:
            self.models[version_id].status = status
            self._save_registry()
            self.logger.info(f"Updated model {version_id} status to {status.value}")
    
    def update_model_metrics(self, version_id: str, metrics: ModelMetrics):
        """Update model metrics."""
        if version_id in self.models:
            self.models[version_id].metrics = metrics
            self._save_registry()
            self.logger.info(f"Updated metrics for model {version_id}")
    
    def get_latest_model(self, model_type: ModelType, status: ModelStatus = ModelStatus.DEPLOYED) -> Optional[ModelVersion]:
        """Get the latest model of a specific type and status."""
        models = self.list_models(model_type=model_type, status=status)
        return models[0] if models else None
    
    def deprecate_model(self, version_id: str, reason: str):
        """Deprecate a model version."""
        if version_id in self.models:
            self.models[version_id].status = ModelStatus.DEPRECATED
            self.models[version_id].config['deprecation_reason'] = reason
            self.models[version_id].config['deprecated_at'] = datetime.utcnow().isoformat()
            self._save_registry()
            self.logger.info(f"Deprecated model {version_id}: {reason}")


class TrainingPipeline:
    """Manage AI model training pipelines."""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.active_jobs: Dict[str, TrainingJob] = {}
        self.logger = logging.getLogger(__name__)
    
    async def start_training_job(
        self,
        model_type: ModelType,
        config: Dict[str, Any],
        dataset_path: str,
        job_name: Optional[str] = None
    ) -> str:
        """Start a new training job."""
        
        job_id = hashlib.sha256(f"{model_type.value}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:12]
        
        job = TrainingJob(
            job_id=job_id,
            model_type=model_type,
            config=config,
            dataset_path=dataset_path,
            status="queued",
            created_at=datetime.utcnow()
        )
        
        self.active_jobs[job_id] = job
        
        # Start training in background
        asyncio.create_task(self._run_training_job(job))
        
        self.logger.info(f"Started training job: {job_id}")
        return job_id
    
    async def _run_training_job(self, job: TrainingJob):
        """Run a training job."""
        try:
            job.status = "running"
            job.started_at = datetime.utcnow()
            
            # Simulate training process
            for i in range(10):
                await asyncio.sleep(1)  # Simulate training time
                job.progress = (i + 1) / 10
                job.logs.append(f"Training epoch {i+1}/10 completed")
                
                if job.status == "cancelled":
                    job.logs.append("Training job cancelled")
                    return
            
            # Simulate model evaluation
            metrics = ModelMetrics(
                accuracy=0.85 + (hash(job.job_id) % 100) / 1000,  # Simulate varying results
                precision=0.82 + (hash(job.job_id) % 100) / 1000,
                recall=0.88 + (hash(job.job_id) % 100) / 1000,
                f1_score=0.85 + (hash(job.job_id) % 100) / 1000,
                response_time_ms=120.0 + (hash(job.job_id) % 50),
                token_efficiency=0.75 + (hash(job.job_id) % 100) / 1000
            )
            
            # Register the trained model
            version_id = self.model_registry.register_model(
                model_type=job.model_type,
                name=f"{job.model_type.value}_v{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                description=f"Model trained by job {job.job_id}",
                config=job.config,
                artifacts_path=f"models/{job.job_id}",
                created_by="training_pipeline",
                metrics=metrics
            )
            
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result_metrics = metrics
            job.logs.append(f"Training completed. Model registered as {version_id}")
            
        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.logs.append(f"Training failed: {e}")
            self.logger.error(f"Training job {job.job_id} failed: {e}")
    
    def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job status."""
        return self.active_jobs.get(job_id)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a training job."""
        if job_id in self.active_jobs:
            self.active_jobs[job_id].status = "cancelled"
            return True
        return False
    
    def list_jobs(self, status: Optional[str] = None) -> List[TrainingJob]:
        """List training jobs."""
        jobs = list(self.active_jobs.values())
        if status:
            jobs = [job for job in jobs if job.status == status]
        return sorted(jobs, key=lambda x: x.created_at, reverse=True)


class ModelDeploymentManager:
    """Manage model deployments and A/B testing."""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.deployments = {}
        self.logger = logging.getLogger(__name__)
    
    def deploy_model(
        self,
        version_id: str,
        deployment_name: str,
        traffic_percentage: float = 100.0,
        rollback_threshold: Optional[Dict[str, float]] = None
    ) -> bool:
        """Deploy a model version."""
        
        model = self.model_registry.get_model(version_id)
        if not model:
            self.logger.error(f"Model version {version_id} not found")
            return False
        
        if model.status != ModelStatus.READY:
            self.logger.error(f"Model {version_id} is not ready for deployment")
            return False
        
        deployment_config = {
            "version_id": version_id,
            "deployment_name": deployment_name,
            "traffic_percentage": traffic_percentage,
            "deployed_at": datetime.utcnow().isoformat(),
            "rollback_threshold": rollback_threshold or {},
            "status": "active"
        }
        
        self.deployments[deployment_name] = deployment_config
        self.model_registry.update_model_status(version_id, ModelStatus.DEPLOYED)
        
        self.logger.info(f"Deployed model {version_id} as {deployment_name}")
        return True
    
    def rollback_deployment(self, deployment_name: str, reason: str) -> bool:
        """Rollback a deployment."""
        
        if deployment_name not in self.deployments:
            return False
        
        deployment = self.deployments[deployment_name]
        deployment["status"] = "rolled_back"
        deployment["rollback_reason"] = reason
        deployment["rolled_back_at"] = datetime.utcnow().isoformat()
        
        # Find previous stable deployment
        # This is a simplified implementation
        previous_deployments = [
            d for d in self.deployments.values()
            if d["deployment_name"] != deployment_name and d["status"] == "active"
        ]
        
        if previous_deployments:
            # Activate the most recent previous deployment
            latest_deployment = max(previous_deployments, key=lambda x: x["deployed_at"])
            latest_deployment["traffic_percentage"] = 100.0
            self.logger.info(f"Rolled back to deployment: {latest_deployment['deployment_name']}")
        
        return True
    
    def update_traffic_split(self, traffic_splits: Dict[str, float]) -> bool:
        """Update traffic splits between deployments."""
        
        total_traffic = sum(traffic_splits.values())
        if abs(total_traffic - 100.0) > 0.1:  # Allow small floating point errors
            self.logger.error(f"Traffic splits must sum to 100%, got {total_traffic}%")
            return False
        
        for deployment_name, percentage in traffic_splits.items():
            if deployment_name in self.deployments:
                self.deployments[deployment_name]["traffic_percentage"] = percentage
        
        self.logger.info(f"Updated traffic splits: {traffic_splits}")
        return True
    
    def get_active_deployments(self) -> Dict[str, Dict[str, Any]]:
        """Get all active deployments."""
        return {
            name: config for name, config in self.deployments.items()
            if config["status"] == "active"
        }


class ModelMonitor:
    """Monitor model performance in production."""
    
    def __init__(self, model_registry: ModelRegistry):
        self.model_registry = model_registry
        self.metrics_history = {}
        self.alerts = []
        self.logger = logging.getLogger(__name__)
    
    def record_prediction(
        self,
        model_version_id: str,
        input_data: Dict[str, Any],
        prediction: Any,
        response_time_ms: float,
        user_feedback: Optional[float] = None
    ):
        """Record a model prediction for monitoring."""
        
        if model_version_id not in self.metrics_history:
            self.metrics_history[model_version_id] = []
        
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "input_data": input_data,
            "prediction": prediction,
            "response_time_ms": response_time_ms,
            "user_feedback": user_feedback
        }
        
        self.metrics_history[model_version_id].append(record)
        
        # Keep only last 1000 records per model
        if len(self.metrics_history[model_version_id]) > 1000:
            self.metrics_history[model_version_id] = self.metrics_history[model_version_id][-1000:]
        
        # Check for performance degradation
        self._check_performance_alerts(model_version_id)
    
    def _check_performance_alerts(self, model_version_id: str):
        """Check for performance degradation and create alerts."""
        
        if model_version_id not in self.metrics_history:
            return
        
        recent_records = self.metrics_history[model_version_id][-50:]  # Last 50 predictions
        
        if len(recent_records) < 10:
            return
        
        # Check response time
        avg_response_time = sum(r["response_time_ms"] for r in recent_records) / len(recent_records)
        if avg_response_time > 5000:  # 5 seconds
            self._create_alert(
                model_version_id,
                "high_response_time",
                f"Average response time: {avg_response_time:.2f}ms"
            )
        
        # Check user feedback
        feedback_scores = [r["user_feedback"] for r in recent_records if r["user_feedback"] is not None]
        if feedback_scores:
            avg_feedback = sum(feedback_scores) / len(feedback_scores)
            if avg_feedback < 0.6:  # 60% satisfaction threshold
                self._create_alert(
                    model_version_id,
                    "low_satisfaction",
                    f"Average user satisfaction: {avg_feedback:.2f}"
                )
    
    def _create_alert(self, model_version_id: str, alert_type: str, message: str):
        """Create a performance alert."""
        
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "model_version_id": model_version_id,
            "alert_type": alert_type,
            "message": message,
            "severity": "warning"
        }
        
        self.alerts.append(alert)
        self.logger.warning(f"Model alert: {alert}")
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
    
    def get_model_metrics(self, model_version_id: str, hours_back: int = 24) -> Dict[str, Any]:
        """Get aggregated metrics for a model."""
        
        if model_version_id not in self.metrics_history:
            return {}
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        recent_records = [
            r for r in self.metrics_history[model_version_id]
            if datetime.fromisoformat(r["timestamp"]) > cutoff_time
        ]
        
        if not recent_records:
            return {}
        
        # Calculate metrics
        response_times = [r["response_time_ms"] for r in recent_records]
        feedback_scores = [r["user_feedback"] for r in recent_records if r["user_feedback"] is not None]
        
        metrics = {
            "total_predictions": len(recent_records),
            "avg_response_time_ms": sum(response_times) / len(response_times),
            "max_response_time_ms": max(response_times),
            "min_response_time_ms": min(response_times),
            "predictions_per_hour": len(recent_records) / hours_back
        }
        
        if feedback_scores:
            metrics.update({
                "avg_user_satisfaction": sum(feedback_scores) / len(feedback_scores),
                "feedback_count": len(feedback_scores)
            })
        
        return metrics
    
    def get_recent_alerts(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        return [
            alert for alert in self.alerts
            if datetime.fromisoformat(alert["timestamp"]) > cutoff_time
        ]


# Factory functions for dependency injection
def create_model_registry() -> ModelRegistry:
    """Create model registry instance."""
    return ModelRegistry()


def create_training_pipeline(model_registry: ModelRegistry) -> TrainingPipeline:
    """Create training pipeline instance."""
    return TrainingPipeline(model_registry)


def create_deployment_manager(model_registry: ModelRegistry) -> ModelDeploymentManager:
    """Create deployment manager instance."""
    return ModelDeploymentManager(model_registry)


def create_model_monitor(model_registry: ModelRegistry) -> ModelMonitor:
    """Create model monitor instance."""
    return ModelMonitor(model_registry)
