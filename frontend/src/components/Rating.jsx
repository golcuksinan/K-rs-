export default function Rating({

value=0

}){


return (

<div className="flex gap-1">

{

Array.from({

length:5

}).map((_,index)=>(


<span

key={index}

className={

index < value

?

"text-yellow-500"

:

"text-gray-300"

}

>

★

</span>


))

}


</div>

);

}