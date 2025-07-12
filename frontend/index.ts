interface Script {
    title: string,
    audio_text: string,
    audio_data: string,
    image_data: string,
}

window.onload = () => {
    console.log("Page loaded!");
    const title_element: HTMLElement = document.getElementById("script-title")!;
    const img_element: HTMLImageElement = document.getElementById("script-img") as HTMLImageElement;
    script_loop("http://localhost:8080/next", img_element, title_element);
}

async function script_loop(url: string, img_element: HTMLImageElement, title_element: HTMLElement) {
    const response = await fetch(url);
    const script: Script = await response.json();
    console.log(script);
    const dataUri: string = `data:image/png;base64,${script.image_data}`;
    img_element.src = dataUri;
    title_element.textContent = script.title;
}