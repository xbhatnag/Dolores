"use strict";
var __awaiter = (this && this.__awaiter) || function (thisArg, _arguments, P, generator) {
    function adopt(value) { return value instanceof P ? value : new P(function (resolve) { resolve(value); }); }
    return new (P || (P = Promise))(function (resolve, reject) {
        function fulfilled(value) { try { step(generator.next(value)); } catch (e) { reject(e); } }
        function rejected(value) { try { step(generator["throw"](value)); } catch (e) { reject(e); } }
        function step(result) { result.done ? resolve(result.value) : adopt(result.value).then(fulfilled, rejected); }
        step((generator = generator.apply(thisArg, _arguments || [])).next());
    });
};
window.onload = () => {
    console.log("Page loaded!");
    const title_element = document.getElementById("script-title");
    const img_element = document.getElementById("script-img");
    script_loop("http://localhost:8080/next", img_element, title_element);
};
function script_loop(url, img_element, title_element) {
    return __awaiter(this, void 0, void 0, function* () {
        const response = yield fetch(url);
        const script = yield response.json();
        console.log(script);
        const dataUri = `data:image/png;base64,${script.image_data}`;
        img_element.src = dataUri;
        title_element.textContent = script.title;
    });
}
