<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { browser } from '$app/environment';
    let {v} = $page.params;

    if (browser) {
        goto(`/watch?v=${v}`, { replaceState: true });
    }
</script>
<p>Redirecting…</p>
