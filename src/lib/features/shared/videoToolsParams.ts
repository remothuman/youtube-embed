import { goto } from '$app/navigation';

export function getActiveTools(url: URL): string[] {
	const toolsParam = url.searchParams.get('tools');
	if (!toolsParam) return [];
	return toolsParam.split(',').filter(Boolean);
}

export function updateToolsParam(url: URL, toolName: string, active: boolean) {
	const newUrl = new URL(url);
	const currentTools = getActiveTools(newUrl);

	if (active && !currentTools.includes(toolName)) {
		currentTools.push(toolName);
	} else if (!active) {
		const idx = currentTools.indexOf(toolName);
		if (idx > -1) currentTools.splice(idx, 1);
	}

	if (currentTools.length > 0) {
		newUrl.searchParams.set('tools', currentTools.join(','));
	} else {
		newUrl.searchParams.delete('tools');
	}

	goto(newUrl.toString(), { replaceState: true, keepFocus: true });
}

export function isToolActive(url: URL, toolName: string): boolean {
	return getActiveTools(url).includes(toolName);
}
