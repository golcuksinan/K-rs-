const API_URL =
import.meta.env.VITE_API_URL;



async function apiRequest(
endpoint,
options={}
){


const response = await fetch(

`${API_URL}${endpoint}`,

{

headers:{

"Content-Type":
"application/json"

},

...options

}

);



if(!response.ok){

throw new Error(
"Bir hata oluştu."
);

}


return response.json();


}



export const api = {


get(endpoint){

return apiRequest(endpoint);

},



post(endpoint,data){

return apiRequest(

endpoint,

{

method:"POST",

body:
JSON.stringify(data)

}

);

},



put(endpoint,data){

return apiRequest(

endpoint,

{

method:"PUT",

body:
JSON.stringify(data)

}

);

},



delete(endpoint){

return apiRequest(

endpoint,

{

method:"DELETE"

}

);

}


};