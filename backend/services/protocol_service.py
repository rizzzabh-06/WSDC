"""
WSDC Protocol Service — Feature 4.6 (Protocol Model Builder).
Extracts the contract architecture from Slither's Python AST and parses user-defined `.wsdc/protocol.yaml`.
"""

import logging
import os
import yaml
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from models import ProtocolModel
from config import get_settings

logger = logging.getLogger("wsdc.protocol_service")

def extract_architecture(repo_dir: str) -> Dict[str, Any]:
    """
    Uses the Slither Python API to parse the repo and extract inheritance trees and key roles.
    Returns:
        {"contracts": [...], "trust_edges": [...]}
    """
    try:
        from slither.slither import Slither
        from slither.exceptions import SlitherError
        
        logger.info("Extracting Protocol Architecture for %s", repo_dir)
        slither = Slither(repo_dir)
        
        contracts = []
        trust_edges = []
        
        for contract in slither.contracts:
            roles = []
            
            # Extract common OpenZeppelin security roles from inheritance
            inheritance_names = [c.name for c in contract.inheritance]
            if "Ownable" in inheritance_names:
                roles.append("Ownable")
            if "AccessControl" in inheritance_names:
                roles.append("AccessControl")
            if "ReentrancyGuard" in inheritance_names:
                roles.append("ReentrancyGuard")
            if "Pausable" in inheritance_names:
                roles.append("Pausable")
                
            contracts.append({
                "name": contract.name,
                "file": contract.source_mapping.filename.relative if contract.source_mapping else "",
                "roles": roles,
                "is_interface": contract.is_interface,
                "is_library": contract.is_library,
            })
            
            # Map inheritance trust edges
            for inherited in contract.inheritance:
                trust_edges.append({
                    "from": contract.name,
                    "to": inherited.name,
                    "trust_level": "inheritance",
                    "reason": "inherits from"
                })
                
        logger.info("Successfully extracted architecture: %d contracts", len(contracts))
        return {"contracts": contracts, "trust_edges": trust_edges}
        
    except Exception as e:
        logger.warning("Failed to extract architecture: %s", str(e))
        return {"contracts": [], "trust_edges": []}


def parse_wsdc_config(repo_dir: str) -> Optional[Dict[str, Any]]:
    """
    Reads the repo's `.wsdc/protocol.yaml` if it exists.
    """
    config_path = os.path.join(repo_dir, ".wsdc", "protocol.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                logger.info("Loaded .wsdc/protocol.yaml configuration")
                return config
        except Exception as e:
            logger.error("Failed to parse .wsdc/protocol.yaml: %s", str(e))
    return None


async def upsert_protocol_model(
    session: AsyncSession, 
    repo_uuid: str, 
    architecture: Dict[str, Any], 
    config: Optional[Dict[str, Any]]
) -> ProtocolModel:
    """
    Upserts the synthesized protocol model into the database.
    """
    invariants = config.get("invariants", []) if config else []
    
    stmt = select(ProtocolModel).where(ProtocolModel.repo_id == repo_uuid)
    result = await session.execute(stmt)
    model = result.scalars().first()
    
    if model:
        model.contracts = architecture.get("contracts", [])
        model.trust_edges = architecture.get("trust_edges", [])
        model.invariants = invariants
    else:
        model = ProtocolModel(
            repo_id=repo_uuid,
            contracts=architecture.get("contracts", []),
            trust_edges=architecture.get("trust_edges", []),
            invariants=invariants
        )
        session.add(model)
        
    await session.commit()
    logger.info("Persisted Protocol Model for repo %s", repo_uuid)
    return model
