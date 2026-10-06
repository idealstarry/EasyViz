"""Connect the official MCP SDK stdio client to only the final extracted ZIP."""
import asyncio
import base64
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from check_package import extract_package, validate_plugin
from package_io import file_sha256
from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def probe(script, project, figure, environment):
    params = StdioServerParameters(command=sys.executable,
        args=[str(script), '--project-dir', str(project), '--figure-dir', str(figure)],
        env=environment, cwd=str(project))
    async with Client(params, raise_exceptions=True, read_timeout_seconds=20) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        names = {tool.name for tool in tools.tools}
        assert {'capabilities', 'get_attempt', 'list_requests', 'render_attempt'} <= names
        attempt = await client.call_tool('get_attempt', {})
        assert not attempt.is_error, attempt
        detail = attempt.structured_content
        assert detail['id'] and detail['panel']['width_mm'] > 0 and detail['panel']['height_mm'] > 0
        assert all(Path(path).is_relative_to(project) for path in detail['exports'].values())
        preview = await client.read_resource(detail['preview_resource'])
        assert len(preview.contents) == 1
        item = preview.contents[0]
        raw = base64.b64decode(item.blob) if hasattr(item, 'blob') else item.text.encode()
        image = ET.fromstring(raw)
        assert image.tag.endswith('svg')
        assert any(template.uri_template == 'easyviz://attempt/{attempt_id}/panel.svg'
                   for template in templates.resource_templates)
        return {'status': 'pass', 'protocol_version': client.protocol_version,
                'sdk_version': importlib.metadata.version('mcp'), 'transport': 'official SDK stdio',
                'tool_count': len(tools.tools), 'tools': sorted(names),
                'listed_resources_count': len(resources.resources),
                'resource_templates': [item.uri_template for item in templates.resource_templates],
                'read_only_tool': 'get_attempt', 'actual_attempt_id': detail['id'], 'actual_panel_mm': detail['panel'],
                'scoped_preview_resource_read': True, 'preview_svg_bytes': len(raw),
                'limits': 'Discovery/read-only tool and registered SVG resource only; no write tool, preview job, Agent wake-up or installation.'}


def main():
    build = json.loads((ROOT / 'dist/build.json').read_text())
    archive = ROOT / 'dist' / build['archive']
    assert file_sha256(archive) == build['sha256']
    with tempfile.TemporaryDirectory(prefix='easyviz-final-extracted-mcp-') as temporary:
        project = Path(temporary).resolve()
        count = extract_package(archive, project / 'package')
        plugin = project / 'package/easyviz'
        assert validate_plugin(plugin)['version'] == build['version']
        scripts = plugin / 'skills/easyviz/scripts'
        fixture = plugin / 'skills/easyviz/assets/fixtures/heatmap'
        adopted = json.loads((fixture / 'spec.json').read_text())
        adopted['layout']['font'] = 'DejaVu Sans'
        adopted['formats'] = ['svg', 'pdf', 'png']
        spec = project / 'adopted-spec.json'
        spec.write_text(json.dumps(adopted, indent=2) + '\n')
        figure = project / 'attempt-01'
        environment = {**os.environ, 'MPLBACKEND': 'Agg', 'MPLCONFIGDIR': str(project / 'matplotlib')}
        command = [sys.executable, '-I', '-B', str(scripts / 'render.py'), '--data', str(fixture / 'data.csv'),
                   '--spec', str(spec), '--out', str(figure)]
        run = subprocess.run(command, cwd=project, env=environment, capture_output=True, text=True)
        assert run.returncode == 0, run.stdout + run.stderr
        qa = json.loads((figure / 'qa.json').read_text())
        assert qa['status'] == 'pass' and qa['valid_outputs']
        report = asyncio.run(probe(scripts / 'easyviz_mcp.py', project, figure, environment))
        report.update({'archive': build['archive'], 'archive_sha256': build['sha256'], 'archive_entries': count,
                       'source': 'Final extracted ZIP; both renderer and MCP adapter executed from the temporary package tree.',
                       'new_module_closure': {name: file_sha256(scripts / name) for name in
                            ('analysis_result.py', 'design_mechanisms.py', 'figure_service.py', 'reproduction_checkpoint.py',
                             'easyviz_mcp.py', 'requirements-mcp.txt')}, 'fresh_figure_qa': qa['status']})
    Path(__file__).with_name('extracted-mcp.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
