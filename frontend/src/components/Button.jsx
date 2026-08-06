export default function Button({
    children,
    dark=false
}) {


return (

<button

className={`
px-7
py-3
text-sm
transition-all
duration-300

${
dark

?

"bg-[#102744] text-white hover:bg-[#1b385f]"

:

"border border-[#102744] hover:bg-[#102744] hover:text-white"

}

`}

>

{children}

</button>

);


}